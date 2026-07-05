# Centralized structured logging.
#
# Every layer logs through get_logger(__name__). All app loggers live under the
# "app" namespace and share a single stdout handler, so there are no duplicate
# lines and uvicorn's own loggers stay independent. The formatter injects the
# current request id (or "-") from the request context.

import logging
import sys

from app.core.config import settings
from app.core.request_context import get_execution_id, get_request_id

_ROOT_LOGGER_NAME = "app"
_configured = False


class RequestIdFormatter(logging.Formatter):
    """Formatter that stamps each record with the request and execution ids."""

    def format(self, record: logging.LogRecord) -> str:
        # Read from the context at format time so it always reflects the record's
        # scope, and never crashes when no request/execution is active.
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id() or "-"
        if not hasattr(record, "execution_id"):
            record.execution_id = get_execution_id() or "-"
        return super().format(record)


def configure_logging() -> None:
    """Idempotently configure the shared "app" logger (no duplicate handlers)."""
    global _configured
    if _configured:
        return

    level = logging.DEBUG if settings.DEBUG else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        RequestIdFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s execution_id=%(execution_id)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    app_logger = logging.getLogger(_ROOT_LOGGER_NAME)
    app_logger.setLevel(level)
    app_logger.handlers.clear()  # guard against duplicate handlers on reconfigure
    app_logger.addHandler(handler)
    # Don't propagate to the Python root logger (which uvicorn configures),
    # otherwise every app line would be emitted twice.
    app_logger.propagate = False

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the shared "app" namespace, configuring on first use."""
    configure_logging()
    return logging.getLogger(name)
