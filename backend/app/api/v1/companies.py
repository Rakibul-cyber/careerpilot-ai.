# Company HTTP endpoints (v1) — read-only, all protected.
#
# Thin transport layer: resolve dependencies, delegate to services, translate
# not-found into 404. Soft-deleted rows are already excluded by the repository.

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_company_service, get_current_user, get_db, get_job_service
from app.models.user import User
from app.schemas.company import CompanyRead
from app.schemas.job import JobRead
from app.services.company_service import CompanyService
from app.services.job_service import JobService

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("", response_model=list[CompanyRead])
def list_companies(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    company_service: CompanyService = Depends(get_company_service),
    current_user: User = Depends(get_current_user),
) -> list[CompanyRead]:
    """List companies (newest first), paginated."""
    return company_service.list_companies(db, skip=skip, limit=limit)


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    company_service: CompanyService = Depends(get_company_service),
    current_user: User = Depends(get_current_user),
) -> CompanyRead:
    """Fetch a single company by id."""
    company = company_service.get_company_by_id(db, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return company


@router.get("/{company_id}/jobs", response_model=list[JobRead])
def list_company_jobs(
    company_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    company_service: CompanyService = Depends(get_company_service),
    job_service: JobService = Depends(get_job_service),
    current_user: User = Depends(get_current_user),
) -> list[JobRead]:
    """List jobs for one company (newest first), paginated."""
    company = company_service.get_company_by_id(db, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return job_service.list_jobs_by_company(
        db, company_id=company_id, skip=skip, limit=limit
    )
