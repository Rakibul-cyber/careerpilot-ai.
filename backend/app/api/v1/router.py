# v1 aggregate router.
# Combines all v1 endpoint routers into a single `api_router` that main.py mounts.

from fastapi import APIRouter

from app.api.v1 import auth, companies, jobs, saved_searches, users
from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router)
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(jobs.router)
api_router.include_router(saved_searches.router)
