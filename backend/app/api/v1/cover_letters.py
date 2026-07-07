# Cover letter HTTP endpoints (v1) — all protected, user-scoped.
#
# Thin transport layer over CoverLetterService. A failed AI generation still
# returns 201 with generation_status=failed (the row is persisted); only
# precondition failures surface as errors. The local raw_ai_response is never
# exposed (not in CoverLetterRead).

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_cover_letter_service,
    get_current_user,
    get_db,
)
from app.models.user import User
from app.schemas.cover_letter import CoverLetterCreate, CoverLetterRead
from app.services.cover_letter_service import (
    CoverLetterNotFoundError,
    CoverLetterService,
    JobMatchMismatchError,
    JobMatchNotFoundError,
    JobNotActiveError,
    JobNotFoundError,
    ResumeProfileNotCompletedError,
    ResumeProfileNotFoundError,
)

router = APIRouter(prefix="/cover-letters", tags=["Cover Letters"])


@router.post("", response_model=CoverLetterRead, status_code=status.HTTP_201_CREATED)
def create_cover_letter(
    payload: CoverLetterCreate,
    db: Session = Depends(get_db),
    service: CoverLetterService = Depends(get_cover_letter_service),
    current_user: User = Depends(get_current_user),
) -> CoverLetterRead:
    """Generate a tailored cover letter (AI-backed).

    Returns 201 with the outcome even when generation fails (the row is saved
    with generation_status=failed). Precondition failures: unknown/cross-user
    profile -> 404, profile not completed -> 409, missing/deleted job -> 404,
    inactive job -> 409, unknown/cross-user job_match -> 404, job_match not
    matching the profile+job -> 400.
    """
    try:
        return service.generate(
            db,
            current_user.id,
            payload.resume_profile_id,
            payload.job_id,
            job_match_id=payload.job_match_id,
            language=payload.language,
            tone=payload.tone,
        )
    except (ResumeProfileNotFoundError, JobMatchNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume profile or job match not found",
        ) from None
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        ) from None
    except (ResumeProfileNotCompletedError, JobNotActiveError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except JobMatchMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("", response_model=list[CoverLetterRead])
def list_cover_letters(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    service: CoverLetterService = Depends(get_cover_letter_service),
    current_user: User = Depends(get_current_user),
) -> list[CoverLetterRead]:
    """List the current user's cover letters (newest first), paginated."""
    return service.list_cover_letters(db, current_user.id, skip=skip, limit=limit)


@router.get("/{cover_letter_id}", response_model=CoverLetterRead)
def get_cover_letter(
    cover_letter_id: UUID,
    db: Session = Depends(get_db),
    service: CoverLetterService = Depends(get_cover_letter_service),
    current_user: User = Depends(get_current_user),
) -> CoverLetterRead:
    """Fetch one of the current user's cover letters."""
    try:
        return service.get_cover_letter(db, current_user.id, cover_letter_id)
    except CoverLetterNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover letter not found",
        ) from None


@router.delete("/{cover_letter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cover_letter(
    cover_letter_id: UUID,
    db: Session = Depends(get_db),
    service: CoverLetterService = Depends(get_cover_letter_service),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Soft-delete one of the current user's cover letters."""
    deleted = service.delete_cover_letter(db, current_user.id, cover_letter_id)
    if deleted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover letter not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
