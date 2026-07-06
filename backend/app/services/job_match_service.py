# Business-logic layer for resume-to-job matching (M29).
#
# Verifies ownership and preconditions, runs the deterministic scorer, and
# upserts one JobMatch per (resume_profile, job). No AI / embeddings here.
#
# Preconditions:
#   * profile must belong to the user (else 404 — never confirm another user's)
#   * profile must be parse-completed (else 409)
#   * job must exist and not be soft-deleted (else 404)
#   * job must be ACTIVE (else 409)

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.job import JobStatus
from app.models.job_match import JobMatch
from app.models.resume_profile import ResumeParseStatus
from app.repositories.job_match_repository import JobMatchRepository
from app.repositories.job_repository import JobRepository
from app.repositories.resume_profile_repository import (
    ResumeProfileRepository,
)
from app.services.job_match_scoring_service import JobMatchScoringService

logger = get_logger(__name__)


class ResumeProfileNotFoundError(Exception):
    """Profile missing or owned by another user (-> HTTP 404)."""


class ResumeProfileNotCompletedError(Exception):
    """Profile exists but isn't parse-completed (-> HTTP 409)."""


class JobNotFoundError(Exception):
    """Job missing or soft-deleted (-> HTTP 404)."""


class JobNotActiveError(Exception):
    """Job exists but isn't ACTIVE (-> HTTP 409)."""


class JobMatchNotFoundError(Exception):
    """Match missing or owned by another user (-> HTTP 404)."""


class JobMatchService:
    def __init__(
        self,
        resume_profile_repository: ResumeProfileRepository | None = None,
        job_repository: JobRepository | None = None,
        job_match_repository: JobMatchRepository | None = None,
        scoring_service: JobMatchScoringService | None = None,
    ) -> None:
        self.resume_profile_repository = (
            resume_profile_repository or ResumeProfileRepository()
        )
        self.job_repository = job_repository or JobRepository()
        self.job_match_repository = (
            job_match_repository or JobMatchRepository()
        )
        self.scoring_service = scoring_service or JobMatchScoringService()

    def match(
        self,
        db: Session,
        user_id: uuid.UUID,
        resume_profile_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> JobMatch:
        """Score a profile against a job and upsert the match result."""
        profile = self._require_completed_profile(
            db, user_id, resume_profile_id
        )

        job = self.job_repository.get_by_id(db, job_id)
        if job is None:
            raise JobNotFoundError("Job not found")
        if job.status != JobStatus.ACTIVE:
            raise JobNotActiveError("Job is not active")

        result = self.scoring_service.score(profile, job)

        # Upsert: reuse the existing (profile, job) match so re-running updates
        # rather than duplicating.
        match = self.job_match_repository.get_by_profile_job(
            db, resume_profile_id, job_id, user_id
        )
        is_new = match is None
        if is_new:
            match = JobMatch(
                resume_profile_id=resume_profile_id,
                job_id=job_id,
                user_id=user_id,
            )

        match.overall_score = result.overall_score
        match.skill_score = result.skill_score
        match.title_score = result.title_score
        match.location_score = result.location_score
        match.experience_score = result.experience_score
        match.matched_skills = result.matched_skills
        match.missing_skills = result.missing_skills
        match.match_reasons = result.match_reasons
        match.risk_flags = result.risk_flags
        match.raw_match_data = result.raw_match_data
        match.matched_at = datetime.now(timezone.utc)

        logger.info(
            "Job matched user_id=%s profile_id=%s job_id=%s score=%.2f",
            user_id,
            resume_profile_id,
            job_id,
            result.overall_score,
        )

        if is_new:
            return self.job_match_repository.create(db, match)
        return self.job_match_repository.update(db, match)

    def get_match(
        self, db: Session, user_id: uuid.UUID, match_id: uuid.UUID
    ) -> JobMatch:
        match = self.job_match_repository.get_by_id(db, match_id, user_id)
        if match is None:
            raise JobMatchNotFoundError("Job match not found")
        return match

    def list_matches_for_profile(
        self,
        db: Session,
        user_id: uuid.UUID,
        resume_profile_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[JobMatch]:
        # Validate ownership so a cross-user profile id 404s instead of
        # silently returning an empty list.
        profile = self.resume_profile_repository.get_by_id(
            db, resume_profile_id, user_id
        )
        if profile is None:
            raise ResumeProfileNotFoundError("Resume profile not found")
        return self.job_match_repository.list_by_profile(
            db, resume_profile_id, user_id, skip=skip, limit=limit
        )

    def _require_completed_profile(self, db, user_id, resume_profile_id):
        profile = self.resume_profile_repository.get_by_id(
            db, resume_profile_id, user_id
        )
        if profile is None:
            raise ResumeProfileNotFoundError("Resume profile not found")
        if profile.parse_status != ResumeParseStatus.COMPLETED:
            raise ResumeProfileNotCompletedError(
                "Resume profile has not completed parsing"
            )
        return profile
