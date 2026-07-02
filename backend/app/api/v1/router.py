# v1 aggregate router.
# Combines all v1 endpoint routers into a single `api_router` that main.py mounts.

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
