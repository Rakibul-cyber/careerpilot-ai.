# Resume HTTP endpoints (v1) — all protected, user-scoped.
#
# Thin transport layer: multipart upload + CRUD, delegating to ResumeService.
# Domain errors map to HTTP: unsupported type -> 400, too large -> 413, missing
# resume -> 404. The local file_path is never exposed (not in ResumeRead).

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_resume_service
from app.models.user import User
from app.schemas.resume import ResumeRead, ResumeTextRead
from app.services.resume_service import (
    FileTooLargeError,
    ResumeService,
    UnsupportedFileTypeError,
)

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
def upload_resume(
    file: UploadFile = File(...),
    is_primary: bool = Form(False),
    db: Session = Depends(get_db),
    service: ResumeService = Depends(get_resume_service),
    current_user: User = Depends(get_current_user),
) -> ResumeRead:
    """Upload a PDF/DOCX resume; stores it and extracts text."""
    try:
        return service.upload_resume(
            db, current_user.id, file, is_primary=is_primary
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        )


@router.get("", response_model=list[ResumeRead])
def list_resumes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    service: ResumeService = Depends(get_resume_service),
    current_user: User = Depends(get_current_user),
) -> list[ResumeRead]:
    """List the current user's resumes (newest first), paginated."""
    return service.list_resumes(db, current_user.id, skip=skip, limit=limit)


@router.get("/{resume_id}", response_model=ResumeRead)
def get_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
    service: ResumeService = Depends(get_resume_service),
    current_user: User = Depends(get_current_user),
) -> ResumeRead:
    """Fetch metadata for one of the current user's resumes."""
    resume = service.get_resume(db, current_user.id, resume_id)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
        )
    return resume


@router.get("/{resume_id}/text", response_model=ResumeTextRead)
def get_resume_text(
    resume_id: UUID,
    db: Session = Depends(get_db),
    service: ResumeService = Depends(get_resume_service),
    current_user: User = Depends(get_current_user),
) -> ResumeTextRead:
    """Fetch the extracted text of one of the current user's resumes."""
    resume = service.get_resume_text(db, current_user.id, resume_id)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
        )
    return resume


@router.post("/{resume_id}/primary", response_model=ResumeRead)
def set_primary_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
    service: ResumeService = Depends(get_resume_service),
    current_user: User = Depends(get_current_user),
) -> ResumeRead:
    """Mark one of the current user's resumes as primary."""
    resume = service.set_primary_resume(db, current_user.id, resume_id)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
        )
    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
    service: ResumeService = Depends(get_resume_service),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Soft-delete one of the current user's resumes."""
    resume = service.delete_resume(db, current_user.id, resume_id)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
