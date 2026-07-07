# Application HTTP endpoints (v1) -- protected, user-scoped ATS operations.

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_application_service,
    get_current_user,
    get_db,
)
from app.domain.application.transitions import (
    InvalidApplicationStatusTransitionError,
    InvalidInitialApplicationStatusError,
)
from app.models.application import ApplicationSource, ApplicationStatus
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationFilter,
    ApplicationRead,
    ApplicationStatusUpdate,
    ApplicationUpdate,
)
from app.services.application_service import (
    ApplicationNotFoundError,
    ApplicationResourceMismatchError,
    ApplicationResourceNotFoundError,
    ApplicationService,
    InvalidApplicationDataError,
)

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post(
    "",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service),
    current_user: User = Depends(get_current_user),
) -> ApplicationRead:
    """Create a job application linked to existing job/profile artifacts."""
    try:
        return service.create_application(db, current_user.id, payload)
    except ApplicationResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (
        ApplicationResourceMismatchError,
        InvalidApplicationDataError,
        InvalidInitialApplicationStatusError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("", response_model=list[ApplicationRead])
def list_applications(
    status_filter: ApplicationStatus | None = Query(None, alias="status"),
    company: str | None = None,
    source: ApplicationSource | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service),
    current_user: User = Depends(get_current_user),
) -> list[ApplicationRead]:
    """List current user's applications with simple filters and pagination."""
    filters = ApplicationFilter(
        status=status_filter,
        company=company,
        source=source,
        date_from=date_from,
        date_to=date_to,
    )
    return service.list_applications(
        db, current_user.id, filters=filters, skip=skip, limit=limit
    )


@router.get("/{application_id}", response_model=ApplicationRead)
def get_application(
    application_id: UUID,
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service),
    current_user: User = Depends(get_current_user),
) -> ApplicationRead:
    """Fetch one of the current user's applications."""
    try:
        return service.get_application(db, current_user.id, application_id)
    except ApplicationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        ) from None


@router.patch("/{application_id}", response_model=ApplicationRead)
def update_application(
    application_id: UUID,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service),
    current_user: User = Depends(get_current_user),
) -> ApplicationRead:
    """Patch editable application metadata."""
    try:
        return service.update_application(db, current_user.id, application_id, payload)
    except ApplicationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        ) from None
    except ApplicationResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ApplicationResourceMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.patch("/{application_id}/status", response_model=ApplicationRead)
def update_application_status(
    application_id: UUID,
    payload: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service),
    current_user: User = Depends(get_current_user),
) -> ApplicationRead:
    """Move an application through the explicit ATS lifecycle."""
    try:
        return service.update_status(
            db, current_user.id, application_id, payload.status
        )
    except ApplicationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        ) from None
    except InvalidApplicationStatusTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: UUID,
    db: Session = Depends(get_db),
    service: ApplicationService = Depends(get_application_service),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Soft-delete one of the current user's applications."""
    deleted = service.delete_application(db, current_user.id, application_id)
    if deleted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
