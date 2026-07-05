# Application entrypoint.
# Assembles the FastAPI app and mounts the versioned API router.

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.request_context import RequestIDMiddleware

# Configure the shared logger before anything logs.
configure_logging()
logger = get_logger(__name__)

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

# Request-id + request logging must wrap every request, so register it first.
app.add_middleware(RequestIDMiddleware)

# Mount all v1 routes under the configured prefix.
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

logger.info("CareerPilot AI application initialized")


@app.get("/")
async def root() -> dict:
    return {"message": "Welcome to CareerPilot AI API"}
