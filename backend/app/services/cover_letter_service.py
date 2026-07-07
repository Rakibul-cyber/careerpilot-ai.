# Business-logic layer for AI cover-letter generation (M30).
#
# Verifies ownership/preconditions, assembles a plain-dict context from the
# ResumeProfile + Job (+ optional JobMatch), calls the AICoverLetterClient
# abstraction (never a provider SDK directly), validates the AI output, and
# persists exactly one CoverLetter row — including a FAILED row when generation
# or validation fails (the failure is captured, not raised to the caller).

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.cover_letter import CoverLetter, CoverLetterStatus
from app.models.job import JobStatus
from app.models.job_match import JobMatch
from app.models.resume_profile import ResumeParseStatus, ResumeProfile
from app.repositories.cover_letter_repository import CoverLetterRepository
from app.repositories.job_match_repository import JobMatchRepository
from app.repositories.job_repository import JobRepository
from app.repositories.resume_profile_repository import (
    ResumeProfileRepository,
)
from app.schemas.cover_letter import CoverLetterAIOutput
from app.services.ai.anthropic_cover_letter_client import (
    AnthropicCoverLetterClient,
)
from app.services.ai.base_cover_letter_client import AICoverLetterClient

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
    """Provided job_match missing or owned by another user (-> HTTP 404)."""


class JobMatchMismatchError(Exception):
    """job_match doesn't belong to the given profile + job (-> HTTP 400)."""


class CoverLetterNotFoundError(Exception):
    """Cover letter missing or owned by another user (-> HTTP 404)."""


class CoverLetterService:
    def __init__(
        self,
        cover_letter_repository: CoverLetterRepository | None = None,
        resume_profile_repository: ResumeProfileRepository | None = None,
        job_repository: JobRepository | None = None,
        job_match_repository: JobMatchRepository | None = None,
        cover_letter_client: AICoverLetterClient | None = None,
    ) -> None:
        self.cover_letter_repository = (
            cover_letter_repository or CoverLetterRepository()
        )
        self.resume_profile_repository = (
            resume_profile_repository or ResumeProfileRepository()
        )
        self.job_repository = job_repository or JobRepository()
        self.job_match_repository = job_match_repository or JobMatchRepository()
        self.cover_letter_client = cover_letter_client or AnthropicCoverLetterClient()

    def generate(
        self,
        db: Session,
        user_id: uuid.UUID,
        resume_profile_id: uuid.UUID,
        job_id: uuid.UUID,
        job_match_id: uuid.UUID | None = None,
        language: str = "en",
        tone: str = "professional",
    ) -> CoverLetter:
        """Generate and persist a tailored cover letter (always creates a row).

        Precondition failures raise; AI/validation failures are captured on a
        FAILED row rather than raised.
        """
        profile = self._require_completed_profile(db, user_id, resume_profile_id)

        job = self.job_repository.get_by_id(db, job_id)
        if job is None:
            raise JobNotFoundError("Job not found")
        if job.status != JobStatus.ACTIVE:
            raise JobNotActiveError("Job is not active")

        match = self._resolve_match(
            db, user_id, job_match_id, resume_profile_id, job_id
        )

        cover_letter = CoverLetter(
            user_id=user_id,
            resume_profile_id=resume_profile_id,
            job_id=job_id,
            job_match_id=job_match_id,
            language=language,
            tone=tone,
            generation_status=CoverLetterStatus.PENDING,
        )

        raw_response: str | None = None
        try:
            raw_response = self.cover_letter_client.generate_cover_letter(
                profile=self._profile_context(profile),
                job=self._job_context(job),
                match=self._match_context(match),
                language=language,
                tone=tone,
            )
            cover_letter.raw_ai_response = raw_response
            parsed = CoverLetterAIOutput.model_validate_json(raw_response)
            cover_letter.content = parsed.content
            cover_letter.generation_status = CoverLetterStatus.COMPLETED
            cover_letter.generation_error = None
            cover_letter.generated_at = datetime.now(UTC)
            logger.info(
                "Cover letter generated user_id=%s job_id=%s chars=%d",
                user_id,
                job_id,
                len(parsed.content),
            )
        except Exception as exc:
            cover_letter.raw_ai_response = raw_response
            cover_letter.generation_status = CoverLetterStatus.FAILED
            cover_letter.generation_error = f"{type(exc).__name__}: {exc}"
            cover_letter.generated_at = datetime.now(UTC)
            logger.exception(
                "Cover letter generation failed user_id=%s job_id=%s",
                user_id,
                job_id,
            )

        return self.cover_letter_repository.create(db, cover_letter)

    def get_cover_letter(
        self, db: Session, user_id: uuid.UUID, cover_letter_id: uuid.UUID
    ) -> CoverLetter:
        cover_letter = self.cover_letter_repository.get_by_id(
            db, cover_letter_id, user_id
        )
        if cover_letter is None:
            raise CoverLetterNotFoundError("Cover letter not found")
        return cover_letter

    def list_cover_letters(
        self, db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list[CoverLetter]:
        return self.cover_letter_repository.list_by_user(
            db, user_id, skip=skip, limit=limit
        )

    def delete_cover_letter(
        self, db: Session, user_id: uuid.UUID, cover_letter_id: uuid.UUID
    ) -> CoverLetter | None:
        cover_letter = self.cover_letter_repository.get_by_id(
            db, cover_letter_id, user_id
        )
        if cover_letter is None:
            return None
        return self.cover_letter_repository.soft_delete(db, cover_letter)

    # --- helpers -----------------------------------------------------------

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

    def _resolve_match(
        self, db, user_id, job_match_id, resume_profile_id, job_id
    ) -> JobMatch | None:
        if job_match_id is None:
            return None
        match = self.job_match_repository.get_by_id(db, job_match_id, user_id)
        if match is None:
            # Missing or another user's — never confirm existence.
            raise JobMatchNotFoundError("Job match not found")
        if match.resume_profile_id != resume_profile_id or match.job_id != job_id:
            raise JobMatchMismatchError(
                "job_match does not belong to the given profile and job"
            )
        return match

    @staticmethod
    def _profile_context(profile: ResumeProfile) -> dict:
        return {
            "full_name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.location,
            "summary": profile.summary,
            "skills": profile.skills or [],
            "work_experience": profile.work_experience or [],
            "education": profile.education or [],
            "projects": profile.projects or [],
            "certifications": profile.certifications or [],
            "languages": profile.languages or [],
        }

    @staticmethod
    def _job_context(job) -> dict:
        return {
            "title": job.title,
            "company": job.company.name if job.company else None,
            "location": job.location,
            "employment_type": job.employment_type,
            "remote_type": job.remote_type,
            "description": job.description,
            "requirements": job.requirements,
        }

    @staticmethod
    def _match_context(match: JobMatch | None) -> dict | None:
        if match is None:
            return None
        return {
            "overall_score": match.overall_score,
            "matched_skills": match.matched_skills or [],
            "missing_skills": match.missing_skills or [],
            "match_reasons": match.match_reasons or [],
        }
