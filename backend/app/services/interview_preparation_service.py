# Business-logic layer for AI interview preparation (M34).

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.application import ApplicationStatus
from app.models.interview_preparation import (
    InterviewPreparation,
    InterviewPreparationStatus,
)
from app.repositories.application_repository import ApplicationRepository
from app.repositories.interview_preparation_repository import (
    InterviewPreparationRepository,
)
from app.repositories.job_match_repository import JobMatchRepository
from app.schemas.interview_preparation import InterviewPreparationAIOutput
from app.services.ai.anthropic_interview_client import (
    AnthropicInterviewPreparationClient,
)
from app.services.ai.base_interview_client import (
    AIInterviewPreparationClient,
)

logger = get_logger(__name__)


class InterviewPreparationNotFoundError(Exception):
    """Preparation missing or owned by another user (-> HTTP 404)."""


class InterviewPreparationApplicationNotFoundError(Exception):
    """Application missing/deleted or owned by another user (-> HTTP 404)."""


class InterviewPreparationApplicationNotReadyError(Exception):
    """Application is DRAFT, so interview prep is premature (-> HTTP 409)."""


class InterviewPreparationService:
    def __init__(
        self,
        interview_preparation_repository: (
            InterviewPreparationRepository | None
        ) = None,
        application_repository: ApplicationRepository | None = None,
        job_match_repository: JobMatchRepository | None = None,
        interview_client: AIInterviewPreparationClient | None = None,
    ) -> None:
        self.interview_preparation_repository = (
            interview_preparation_repository or InterviewPreparationRepository()
        )
        self.application_repository = application_repository or ApplicationRepository()
        self.job_match_repository = job_match_repository or JobMatchRepository()
        self.interview_client = (
            interview_client or AnthropicInterviewPreparationClient()
        )

    def generate(
        self, db: Session, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> InterviewPreparation:
        application = self._require_ready_application(db, user_id, application_id)
        preparation = self._get_or_new(db, user_id, application_id)
        preparation.generation_status = InterviewPreparationStatus.PENDING
        preparation.generation_error = None
        preparation.generated_at = None

        raw_response: str | None = None
        try:
            raw_response = self.interview_client.generate_interview_preparation(
                application=self._application_context(application),
                job=self._job_context(application.job),
                profile=self._profile_context(application.resume_profile),
                cover_letter=self._cover_letter_context(application.cover_letter),
                match=self._match_context(self._find_match(db, user_id, application)),
            )
            parsed = InterviewPreparationAIOutput.model_validate_json(raw_response)
            self._apply_success(preparation, parsed, raw_response)
            logger.info(
                "Interview preparation generated user_id=%s application_id=%s",
                user_id,
                application_id,
            )
        except Exception as exc:
            self._apply_failure(preparation, raw_response, exc)
            logger.exception(
                "Interview preparation generation failed user_id=%s application_id=%s",
                user_id,
                application_id,
            )

        if preparation.id is None:
            return self.interview_preparation_repository.create(db, preparation)
        return self.interview_preparation_repository.update(db, preparation)

    def get_by_application(
        self, db: Session, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> InterviewPreparation:
        self._require_application(db, user_id, application_id)
        preparation = self.interview_preparation_repository.get_by_application(
            db, application_id, user_id
        )
        if preparation is None:
            raise InterviewPreparationNotFoundError("Interview preparation not found")
        return preparation

    def list_by_user(
        self, db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list[InterviewPreparation]:
        return self.interview_preparation_repository.list_by_user(
            db, user_id, skip=skip, limit=limit
        )

    def delete(
        self, db: Session, user_id: uuid.UUID, preparation_id: uuid.UUID
    ) -> InterviewPreparation | None:
        preparation = self.interview_preparation_repository.get_by_id(
            db, preparation_id, user_id
        )
        if preparation is None:
            return None
        return self.interview_preparation_repository.soft_delete(db, preparation)

    # --- helpers ----------------------------------------------------------

    def _get_or_new(self, db, user_id, application_id):
        existing = self.interview_preparation_repository.get_by_application(
            db, application_id, user_id
        )
        if existing is not None:
            return existing
        return InterviewPreparation(
            user_id=user_id,
            application_id=application_id,
            generation_status=InterviewPreparationStatus.PENDING,
        )

    def _require_application(self, db, user_id, application_id):
        application = self.application_repository.get_by_id(db, application_id, user_id)
        if application is None:
            raise InterviewPreparationApplicationNotFoundError("Application not found")
        return application

    def _require_ready_application(self, db, user_id, application_id):
        application = self._require_application(db, user_id, application_id)
        if application.status == ApplicationStatus.DRAFT:
            raise InterviewPreparationApplicationNotReadyError(
                "Interview preparation requires application status READY or later"
            )
        return application

    def _find_match(self, db, user_id, application):
        return self.job_match_repository.get_by_profile_job(
            db,
            application.resume_profile_id,
            application.job_id,
            user_id,
        )

    @staticmethod
    def _apply_success(preparation, parsed, raw_response):
        data = parsed.model_dump(mode="json")
        preparation.raw_ai_response = raw_response
        preparation.summary = data["summary"]
        preparation.strengths = data["strengths"]
        preparation.weaknesses = data["weaknesses"]
        preparation.technical_questions = data["technical_questions"]
        preparation.behavioral_questions = data["behavioral_questions"]
        preparation.company_questions = data["company_questions"]
        preparation.study_topics = data["study_topics"]
        preparation.interview_tips = data["interview_tips"]
        preparation.estimated_difficulty = parsed.estimated_difficulty
        preparation.generation_status = InterviewPreparationStatus.COMPLETED
        preparation.generation_error = None
        preparation.generated_at = datetime.now(UTC)

    @staticmethod
    def _apply_failure(preparation, raw_response, exc):
        preparation.raw_ai_response = raw_response
        preparation.summary = None
        preparation.strengths = None
        preparation.weaknesses = None
        preparation.technical_questions = None
        preparation.behavioral_questions = None
        preparation.company_questions = None
        preparation.study_topics = None
        preparation.interview_tips = None
        preparation.estimated_difficulty = None
        preparation.generation_status = InterviewPreparationStatus.FAILED
        preparation.generation_error = f"{type(exc).__name__}: {exc}"
        preparation.generated_at = datetime.now(UTC)

    @staticmethod
    def _application_context(application) -> dict:
        return {
            "id": str(application.id),
            "status": application.status.value,
            "source": application.source.value,
            "applied_at": application.applied_at,
            "interview_date": application.interview_date,
            "company_response": application.company_response,
            "notes": application.notes,
        }

    @staticmethod
    def _job_context(job) -> dict:
        return {
            "title": job.title,
            "company": job.company.name if job.company else None,
            "location": job.location,
            "remote_type": job.remote_type,
            "employment_type": job.employment_type,
            "description": job.description,
            "requirements": job.requirements,
        }

    @staticmethod
    def _profile_context(profile) -> dict:
        return {
            "full_name": profile.full_name,
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
    def _cover_letter_context(cover_letter) -> dict | None:
        if cover_letter is None or cover_letter.deleted_at is not None:
            return None
        return {
            "content": cover_letter.content,
            "language": cover_letter.language,
            "tone": cover_letter.tone,
            "generation_status": cover_letter.generation_status.value,
        }

    @staticmethod
    def _match_context(match) -> dict | None:
        if match is None:
            return None
        return {
            "overall_score": match.overall_score,
            "matched_skills": match.matched_skills or [],
            "missing_skills": match.missing_skills or [],
            "match_reasons": match.match_reasons or [],
            "risk_flags": match.risk_flags or [],
        }
