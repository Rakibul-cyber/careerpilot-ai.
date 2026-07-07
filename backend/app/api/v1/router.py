# v1 aggregate router.
# Combines all v1 endpoint routers into a single `api_router` that main.py mounts.

from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    applications,
    auth,
    companies,
    cover_letters,
    interview_preparations,
    job_alerts,
    job_matches,
    job_recommendations,
    jobs,
    resume_profiles,
    resumes,
    saved_searches,
    users,
)
from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(applications.router)
api_router.include_router(analytics.router)
api_router.include_router(users.router)
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(jobs.router)
api_router.include_router(saved_searches.router)
api_router.include_router(job_alerts.router)
api_router.include_router(resumes.router)
api_router.include_router(resume_profiles.router)
api_router.include_router(job_matches.router)
api_router.include_router(job_recommendations.router)
api_router.include_router(cover_letters.router)
api_router.include_router(interview_preparations.router)
