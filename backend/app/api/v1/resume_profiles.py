# ResumeProfile listing endpoint (v1) — protected, user-scoped.
#
# The parse and single-profile-fetch endpoints live under /resumes/{id}/... in
# resumes.py; this router exposes the flat collection of the current user's
# parsed profiles.

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    get_resume_parser_service,
)
from app.models.user import User
from app.schemas.resume_profile import ResumeProfileRead
from app.services.resume_parser_service import ResumeParserService

router = APIRouter(prefix="/resume-profiles", tags=["Resume Profiles"])


@router.get("", response_model=list[ResumeProfileRead])
def list_resume_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    parser: ResumeParserService = Depends(get_resume_parser_service),
    current_user: User = Depends(get_current_user),
) -> list[ResumeProfileRead]:
    """List the current user's parsed resume profiles (newest first)."""
    return parser.list_profiles(db, current_user.id, skip=skip, limit=limit)
