# Application entrypoint.
# Assembles the FastAPI app, mounts the versioned API router, and manages the
# background scheduler lifecycle.

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.request_context import RequestIDMiddleware
from app.scheduler.scheduler import shutdown_scheduler, start_scheduler

# Configure the shared logger before anything logs.
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the scheduler on startup, shut it down gracefully on exit."""
    configure_logging()
    logger.info("CareerPilot AI application starting")
    app.state.scheduler = start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler(app.state.scheduler)
        logger.info("CareerPilot AI application stopped")


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)

# Request-id + request logging must wrap every request, so register it first.
app.add_middleware(RequestIDMiddleware)

# Mount all v1 routes under the configured prefix.
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root() -> dict:
    return {"message": "Welcome to CareerPilot AI API"}
