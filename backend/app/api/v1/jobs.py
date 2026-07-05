# Job HTTP endpoints (v1) — read-only, all protected.
#
# Thin transport layer: resolve dependencies, delegate to JobService, translate
# not-found into 404. Soft-deleted rows are already excluded by the repository.

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_job_service
from app.models.job import JobSource, JobStatus
from app.models.user import User
from app.schemas.job import JobFilter, JobRead
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=list[JobRead])
def list_jobs(
    query: str | None = None,
    location: str | None = None,
    employment_type: str | None = None,
    remote_type: str | None = None,
    status: JobStatus | None = None,
    source: JobSource | None = None,
    company: str | None = None,
    salary_min: int | None = Query(None, ge=0),
    salary_max: int | None = Query(None, ge=0),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    job_service: JobService = Depends(get_job_service),
    current_user: User = Depends(get_current_user),
) -> list[JobRead]:
    """Search jobs by optional filters, paginated.

    With no ``status`` filter the result is restricted to ACTIVE jobs. Invalid
    ``sort_by`` / ``sort_order`` fall back to ``created_at`` / ``desc``.
    """
    filters = JobFilter(
        query=query,
        location=location,
        employment_type=employment_type,
        remote_type=remote_type,
        status=status,
        source=source,
        company=company,
        salary_min=salary_min,
        salary_max=salary_max,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return job_service.search_jobs(db, filters=filters, skip=skip, limit=limit)


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
