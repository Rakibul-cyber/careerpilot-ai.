# ResumeProfile listing endpoint (v1) — protected, user-scoped.
#
# The parse and single-profile-fetch endpoints live under /resumes/{id}/... in
# resumes.py; this router exposes the flat collection of the current user's
# parsed profiles.

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    get_job_match_service,
    get_job_recommendation_service,
    get_resume_parser_service,
)
from app.models.user import User
from app.schemas.job_match import JobMatchRead
from app.schemas.job_recommendation import JobRecommendationRead
from app.schemas.resume_profile import ResumeProfileRead
from app.services.ai.base_embedding_client import EmbeddingAIError
from app.services.job_match_service import (
    JobMatchService,
    JobNotActiveError,
    JobNotFoundError,
    ResumeProfileNotCompletedError,
    ResumeProfileNotFoundError,
)
from app.services.job_recommendation_service import (
    JobRecommendationService,
    ResumeProfileNotCompletedError as RecoProfileNotCompletedError,
    ResumeProfileNotFoundError as RecoProfileNotFoundError,
)
from app.services.resume_parser_service import (
    ResumeParserService,
)

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


@router.post(
    "/{profile_id}/match/{job_id}",
    response_model=JobMatchRead,
    status_code=status.HTTP_201_CREATED,
)
def match_profile_to_job(
    profile_id: UUID,
    job_id: UUID,
    db: Session = Depends(get_db),
    matcher: JobMatchService = Depends(get_job_match_service),
    current_user: User = Depends(get_current_user),
) -> JobMatchRead:
    """Score one of the user's completed profiles against a job (upsert).

    Deterministic, rule-based — no AI. Unknown/cross-user profile -> 404;
    profile not parse-completed -> 409; missing/deleted job -> 404; inactive
    job -> 409. Re-running updates the existing match rather than duplicating.
    """
    try:
        return matcher.match(db, current_user.id, profile_id, job_id)
    except ResumeProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume profile not found",
        )
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    except ResumeProfileNotCompletedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )
    except JobNotActiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )


@router.get("/{profile_id}/matches", response_model=list[JobMatchRead])
def list_profile_matches(
    profile_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    matcher: JobMatchService = Depends(get_job_match_service),
    current_user: User = Depends(get_current_user),
) -> list[JobMatchRead]:
    """List match results for one of the user's profiles (best score first)."""
    try:
        return matcher.list_matches_for_profile(
            db, current_user.id, profile_id, skip=skip, limit=limit
        )
    except ResumeProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume profile not found",
        )


@router.post(
    "/{profile_id}/recommendations",
    response_model=list[JobRecommendationRead],
)
def generate_recommendations(
    profile_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    service: JobRecommendationService = Depends(
        get_job_recommendation_service
    ),
    current_user: User = Depends(get_current_user),
) -> list[JobRecommendationRead]:
    """Generate ranked job recommendations for a completed profile (upsert).

    Blends semantic search (M31) with deterministic match scoring (M29) — no
    LLM. Candidates are only active, non-deleted, embedded jobs. Unknown/
    cross-user profile -> 404; profile not completed -> 409; embedding provider
    down -> 502. Re-running updates existing recommendations.
    """
    try:
        return service.recommend(
            db, current_user.id, profile_id, limit=limit
        )
    except RecoProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume profile not found",
        )
    except RecoProfileNotCompletedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )
    except EmbeddingAIError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding provider is unavailable",
        )


@router.get(
    "/{profile_id}/recommendations",
    response_model=list[JobRecommendationRead],
)
def list_recommendations(
    profile_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    service: JobRecommendationService = Depends(
        get_job_recommendation_service
    ),
    current_user: User = Depends(get_current_user),
) -> list[JobRecommendationRead]:
    """List recommendations for one of the user's profiles (best score first)."""
    try:
        return service.list_recommendations(
            db, current_user.id, profile_id, skip=skip, limit=limit
        )
    except RecoProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume profile not found",
        )
