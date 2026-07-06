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

from app.api.deps import (
    get_current_user,
    get_db,
    get_resume_parser_service,
    get_resume_service,
)
from app.models.user import User
from app.schemas.resume import ResumeRead, ResumeTextRead
from app.schemas.resume_profile import (
    ResumeProfileParseResponse,
    ResumeProfileRead,
)
from app.services.resume_parser_service import (
    ResumeNotFoundError,
    ResumeNotParsableError,
    ResumeParserService,
)
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


@router.post(
    "/{resume_id}/parse", response_model=ResumeProfileParseResponse
)
def parse_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
    parser: ResumeParserService = Depends(get_resume_parser_service),
    current_user: User = Depends(get_current_user),
) -> ResumeProfileParseResponse:
    """Parse a completed resume into a structured profile (AI-backed, upsert).

    Returns 200 with the outcome even when the AI parse fails — the profile is
    persisted with parse_status=failed and the reason in parse_error. Only
    precondition failures surface as errors: unknown/cross-user resume -> 404,
    resume not yet extracted (or no text) -> 409.
    """
    try:
        profile = parser.parse_resume(db, current_user.id, resume_id)
    except ResumeNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
        )
    except ResumeNotParsableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )
    return ResumeProfileParseResponse(
        resume_id=profile.resume_id,
        parse_status=profile.parse_status,
        parse_error=profile.parse_error,
        profile=ResumeProfileRead.model_validate(profile),
    )


@router.get("/{resume_id}/profile", response_model=ResumeProfileRead)
def get_resume_profile(
    resume_id: UUID,
    db: Session = Depends(get_db),
    parser: ResumeParserService = Depends(get_resume_parser_service),
    current_user: User = Depends(get_current_user),
) -> ResumeProfileRead:
    """Fetch the parsed profile for one of the current user's resumes."""
    profile = parser.get_profile_by_resume(db, current_user.id, resume_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume profile not found",
        )
    return profile


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
