# Interview preparation endpoints (v1) -- protected and user-scoped.

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    get_interview_preparation_service,
)
from app.models.user import User
from app.schemas.interview_preparation import InterviewPreparationRead
from app.services.interview_preparation_service import (
    InterviewPreparationApplicationNotFoundError,
    InterviewPreparationApplicationNotReadyError,
    InterviewPreparationNotFoundError,
    InterviewPreparationService,
)

router = APIRouter(tags=["Interview Preparations"])


@router.post(
    "/applications/{application_id}/interview-preparation",
    response_model=InterviewPreparationRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_interview_preparation(
    application_id: UUID,
    db: Session = Depends(get_db),
    service: InterviewPreparationService = Depends(
        get_interview_preparation_service
    ),
    current_user: User = Depends(get_current_user),
) -> InterviewPreparationRead:
    """Generate or regenerate interview prep for an application."""
    try:
        return service.generate(db, current_user.id, application_id)
    except InterviewPreparationApplicationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    except InterviewPreparationApplicationNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )


@router.get(
    "/applications/{application_id}/interview-preparation",
    response_model=InterviewPreparationRead,
)
def get_interview_preparation_for_application(
    application_id: UUID,
    db: Session = Depends(get_db),
    service: InterviewPreparationService = Depends(
        get_interview_preparation_service
    ),
    current_user: User = Depends(get_current_user),
) -> InterviewPreparationRead:
    """Fetch the current user's prep package for one application."""
    try:
        return service.get_by_application(db, current_user.id, application_id)
    except InterviewPreparationApplicationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    except InterviewPreparationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview preparation not found",
        )


@router.get(
    "/interview-preparations",
    response_model=list[InterviewPreparationRead],
)
def list_interview_preparations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    service: InterviewPreparationService = Depends(
        get_interview_preparation_service
    ),
    current_user: User = Depends(get_current_user),
) -> list[InterviewPreparationRead]:
    """List the current user's interview prep packages."""
    return service.list_by_user(db, current_user.id, skip=skip, limit=limit)


@router.delete(
    "/interview-preparations/{preparation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_interview_preparation(
    preparation_id: UUID,
    db: Session = Depends(get_db),
    service: InterviewPreparationService = Depends(
        get_interview_preparation_service
    ),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Soft-delete one of the current user's interview prep packages."""
    deleted = service.delete(db, current_user.id, preparation_id)
    if deleted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview preparation not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
