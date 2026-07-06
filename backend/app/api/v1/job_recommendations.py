# JobRecommendation fetch endpoint (v1) — protected, user-scoped.
#
# Generation and per-profile listing live under /resume-profiles/... in
# resume_profiles.py; this router exposes a single recommendation by id.

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    get_job_recommendation_service,
)
from app.models.user import User
from app.schemas.job_recommendation import JobRecommendationRead
from app.services.job_recommendation_service import (
    JobRecommendationNotFoundError,
    JobRecommendationService,
)

router = APIRouter(prefix="/job-recommendations", tags=["Job Recommendations"])


@router.get("/{recommendation_id}", response_model=JobRecommendationRead)
def get_job_recommendation(
    recommendation_id: UUID,
    db: Session = Depends(get_db),
    service: JobRecommendationService = Depends(
        get_job_recommendation_service
    ),
    current_user: User = Depends(get_current_user),
) -> JobRecommendationRead:
    """Fetch one of the current user's recommendations by id."""
    try:
        return service.get_recommendation(
            db, current_user.id, recommendation_id
        )
    except JobRecommendationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found",
        )
