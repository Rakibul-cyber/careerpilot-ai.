# Business-logic layer for parsing a resume into a structured ResumeProfile.
#
# Orchestrates: verify the resume belongs to the user and is ready (extraction
# COMPLETED with text) -> call the AI parser client -> validate the raw JSON
# against ResumeProfileAIOutput -> upsert one ResumeProfile row. The AI is
# reached only through an injected AIResumeParserClient abstraction; this
# service never calls a provider SDK directly.
#
# Failure policy: a failed AI call or invalid AI JSON does NOT raise to the
# caller. The profile row is still written with parse_status=FAILED, the reason
# in parse_error, and whatever raw response we received in raw_ai_response, so
# failures are inspectable and retryable.

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.resume import ResumeExtractionStatus
from app.models.resume_profile import ResumeParseStatus, ResumeProfile
from app.repositories.resume_profile_repository import (
    ResumeProfileRepository,
)
from app.repositories.resume_repository import ResumeRepository
from app.schemas.resume_profile import ResumeProfileAIOutput
from app.services.ai.anthropic_resume_parser_client import (
    AnthropicResumeParserClient,
)
from app.services.ai.resume_parser_client import AIResumeParserClient

logger = get_logger(__name__)


class ResumeNotFoundError(Exception):
    """The resume does not exist for this user (-> HTTP 404)."""


class ResumeNotParsableError(Exception):
    """The resume exists but isn't ready to parse (-> HTTP 409).

    Covers a resume whose text extraction hasn't completed or that has no
    extracted text to work from.
    """


class ResumeParserService:
    def __init__(
        self,
        resume_repository: ResumeRepository | None = None,
        resume_profile_repository: ResumeProfileRepository | None = None,
        parser_client: AIResumeParserClient | None = None,
    ) -> None:
        self.resume_repository = resume_repository or ResumeRepository()
        self.resume_profile_repository = (
            resume_profile_repository or ResumeProfileRepository()
        )
        self.parser_client = parser_client or AnthropicResumeParserClient()

    def parse_resume(
        self, db: Session, user_id: uuid.UUID, resume_id: uuid.UUID
    ) -> ResumeProfile:
        """Parse a completed resume into a structured profile (upsert).

        Raises ResumeNotFoundError / ResumeNotParsableError for precondition
        failures. AI/validation failures are captured on the row, not raised.
        """
        resume = self.resume_repository.get_by_id(db, resume_id, user_id)
        if resume is None:
            # Cross-user access collapses to "not found" — never confirm the
            # existence of another user's resume.
            raise ResumeNotFoundError("Resume not found")

        if resume.status != ResumeExtractionStatus.COMPLETED:
            raise ResumeNotParsableError(
                "Resume text extraction has not completed"
            )
        if not resume.extracted_text:
            raise ResumeNotParsableError(
                "Resume has no extracted text to parse"
            )

        # Upsert: reuse the existing profile row if this resume was parsed
        # before, so re-parsing overwrites rather than duplicates.
        profile = self.resume_profile_repository.get_by_resume(
            db, resume_id, user_id
        )
        is_new = profile is None
        if is_new:
            profile = ResumeProfile(resume_id=resume_id, user_id=user_id)

        raw_response: str | None = None
        try:
            raw_response = self.parser_client.parse_resume_text(
                resume.extracted_text
            )
            profile.raw_ai_response = raw_response
            parsed = ResumeProfileAIOutput.model_validate_json(raw_response)
            self._apply_parsed(profile, parsed)
            profile.parse_status = ResumeParseStatus.COMPLETED
            profile.parse_error = None
            profile.parsed_at = datetime.now(timezone.utc)
            logger.info(
                "Resume parsed resume_id=%s profile skills=%d experience=%d",
                resume_id,
                len(parsed.skills),
                len(parsed.work_experience),
            )
        except Exception as exc:
            # Persist the failure instead of raising; keep the raw response (if
            # any) for debugging so a future retry can inspect it.
            profile.raw_ai_response = raw_response
            profile.parse_status = ResumeParseStatus.FAILED
            profile.parse_error = f"{type(exc).__name__}: {exc}"
            profile.parsed_at = datetime.now(timezone.utc)
            logger.exception(
                "Resume parse failed resume_id=%s", resume_id
            )

        if is_new:
            return self.resume_profile_repository.create(db, profile)
        return self.resume_profile_repository.update(db, profile)

    def get_profile_by_resume(
        self, db: Session, user_id: uuid.UUID, resume_id: uuid.UUID
    ) -> ResumeProfile | None:
        return self.resume_profile_repository.get_by_resume(
            db, resume_id, user_id
        )

    def list_profiles(
        self, db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list[ResumeProfile]:
        return self.resume_profile_repository.list_by_user(
            db, user_id, skip=skip, limit=limit
        )

    @staticmethod
    def _apply_parsed(
        profile: ResumeProfile, parsed: ResumeProfileAIOutput
    ) -> None:
        """Copy validated AI output onto the ORM row (sections -> JSONB)."""
        profile.full_name = parsed.full_name
        profile.email = parsed.email
        profile.phone = parsed.phone
        profile.location = parsed.location
        profile.summary = parsed.summary
        profile.skills = parsed.skills
        profile.certifications = parsed.certifications
        profile.languages = parsed.languages
        profile.work_experience = [
            item.model_dump() for item in parsed.work_experience
        ]
        profile.education = [item.model_dump() for item in parsed.education]
        profile.projects = [item.model_dump() for item in parsed.projects]
