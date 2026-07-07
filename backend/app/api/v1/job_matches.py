# JobMatch fetch endpoint (v1) — protected, user-scoped.
#
# Match creation and per-profile listing live under /resume-profiles/... in
# resume_profiles.py; this router exposes a single match by id.

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    get_job_match_service,
)
from app.models.user import User
from app.schemas.job_match import JobMatchRead
from app.services.job_match_service import (
    JobMatchNotFoundError,
    JobMatchService,
)

router = APIRouter(prefix="/job-matches", tags=["Job Matches"])


@router.get("/{match_id}", response_model=JobMatchRead)
def get_job_match(
    match_id: UUID,
    db: Session = Depends(get_db),
    matcher: JobMatchService = Depends(get_job_match_service),
    current_user: User = Depends(get_current_user),
) -> JobMatchRead:
    """Fetch one of the current user's match results by id."""
    try:
        return matcher.get_match(db, current_user.id, match_id)
    except JobMatchNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job match not found"
        ) from None
