# Application entrypoint.
# Assembles the FastAPI app and mounts the versioned API router.

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

# Mount all v1 routes under the configured prefix.
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root() -> dict:
    return {"message": "Welcome to CareerPilot AI API"}
