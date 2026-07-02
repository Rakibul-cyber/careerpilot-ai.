# Job HTTP endpoints (v1) — read-only, all protected.
#
# Thin transport layer: resolve dependencies, delegate to JobService, translate
# not-found into 404. Soft-deleted rows are already excluded by the repository.

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_job_service
from app.models.user import User
from app.schemas.job import JobRead
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=list[JobRead])
def list_jobs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
    current_user: User = Depends(get_current_user),
) -> list[JobRead]:
    """List jobs (newest first), paginated."""
    return job_service.list_jobs(db, skip=skip, limit=limit)


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    """Fetch a single job by id."""
    job = job_service.get_job_by_id(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job
