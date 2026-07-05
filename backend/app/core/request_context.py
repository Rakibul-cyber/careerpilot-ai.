# Request correlation context + request-logging middleware.
#
# Each HTTP request gets a uuid4 request id, stored on request.state and in a
# ContextVar so any layer (services, repositories, connectors) can stamp its
# logs with it via get_request_id(). The middleware also logs request start/
# finish with duration, and logs+re-raises unhandled exceptions.

import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Current request id, or None when no request is in scope (e.g. scripts, startup).
_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

# Current execution id, set by scheduled/background jobs (no HTTP request scope)
# so their logs are correlatable the way requests are.
_execution_id_ctx: ContextVar[str | None] = ContextVar(
    "execution_id", default=None
)


def get_request_id() -> str | None:
    """Return the current request id, or None if not in a request scope."""
    return _request_id_ctx.get()


def get_execution_id() -> str | None:
    """Return the current execution id, or None if not in a scheduled job."""
    return _execution_id_ctx.get()


def set_execution_id(execution_id: str):
    """Set the current execution id; returns the token to reset() it afterward."""
    return _execution_id_ctx.set(execution_id)


def reset_execution_id(token) -> None:
    """Restore the execution id to its previous value using set()'s token."""
    _execution_id_ctx.reset(token)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign a request id, log start/finish/duration, log unhandled errors."""

    async def dispatch(self, request: Request, call_next):
        # Lazy import avoids a logging <-> request_context import cycle.
        from app.core.logging import get_logger

        logger = get_logger("app.request")

        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        token = _request_id_ctx.set(request_id)

        method = request.method
        path = request.url.path
        start = time.perf_counter()

        logger.info("request started %s %s", method, path)
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            # logger.exception records the traceback at ERROR with the request id.
            logger.exception(
                "request failed %s %s after %.1fms", method, path, duration_ms
            )
            raise  # never swallow — let the error stack produce the 500
        else:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "request finished %s %s %s %.1fms",
                method,
                path,
                response.status_code,
                duration_ms,
            )
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            _request_id_ctx.reset(token)
