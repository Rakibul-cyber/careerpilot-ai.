# Business-logic layer for ATS applications (M33).
#
# Application is the central record for a user's interaction with a job. This
# service validates linked resources and delegates lifecycle rules to the
# domain transition service.

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.domain.application.transitions import (
    ApplicationStatusTransitionService,
    InvalidApplicationStatusTransitionError,
    InvalidInitialApplicationStatusError,
)
from app.models.application import Application, ApplicationSource, ApplicationStatus
from app.repositories.application_repository import ApplicationRepository
from app.repositories.cover_letter_repository import CoverLetterRepository
from app.repositories.job_recommendation_repository import (
    JobRecommendationRepository,
)
from app.repositories.job_repository import JobRepository
from app.repositories.resume_profile_repository import ResumeProfileRepository
from app.repositories.resume_repository import ResumeRepository
from app.schemas.application import (
    ApplicationCreate,
    ApplicationFilter,
    ApplicationUpdate,
)


class ApplicationNotFoundError(Exception):
    """Application missing or owned by another user (-> HTTP 404)."""


class ApplicationResourceNotFoundError(Exception):
    """Linked resource missing/deleted or owned by another user (-> HTTP 404)."""


class ApplicationResourceMismatchError(Exception):
    """Linked resource does not match the selected job/profile (-> HTTP 400)."""


class InvalidApplicationDataError(Exception):
    """Payload is incomplete or invalid for this operation (-> HTTP 400)."""


class ApplicationService:
    def __init__(
        self,
        application_repository: ApplicationRepository | None = None,
        job_repository: JobRepository | None = None,
        resume_profile_repository: ResumeProfileRepository | None = None,
        resume_repository: ResumeRepository | None = None,
        cover_letter_repository: CoverLetterRepository | None = None,
        job_recommendation_repository: (
            JobRecommendationRepository | None
        ) = None,
        transition_service: ApplicationStatusTransitionService | None = None,
    ) -> None:
        self.application_repository = (
            application_repository or ApplicationRepository()
        )
        self.job_repository = job_repository or JobRepository()
        self.resume_profile_repository = (
            resume_profile_repository or ResumeProfileRepository()
        )
        self.resume_repository = resume_repository or ResumeRepository()
        self.cover_letter_repository = (
            cover_letter_repository or CoverLetterRepository()
        )
        self.job_recommendation_repository = (
            job_recommendation_repository or JobRecommendationRepository()
        )
        self.transition_service = (
            transition_service or ApplicationStatusTransitionService()
        )

    def create_application(
        self, db: Session, user_id: uuid.UUID, data: ApplicationCreate
    ) -> Application:
        self.transition_service.validate_initial(data.status)
        job_id = data.job_id
        resume_profile_id = data.resume_profile_id
        source = data.source

        recommendation = None
        if data.job_recommendation_id is not None:
            recommendation = self._require_recommendation(
                db, user_id, data.job_recommendation_id
            )
            if job_id is None:
                job_id = recommendation.job_id
            if resume_profile_id is None:
                resume_profile_id = recommendation.resume_profile_id
            if "source" not in data.model_fields_set:
                source = ApplicationSource.RECOMMENDATION

        if job_id is None or resume_profile_id is None:
            raise InvalidApplicationDataError(
                "job_id and resume_profile_id are required unless derived "
                "from job_recommendation_id"
            )

        self._require_live_job(db, job_id)
        self._require_live_profile_and_resume(db, user_id, resume_profile_id)

        if recommendation is not None:
            self._validate_recommendation_links(
                recommendation, job_id, resume_profile_id
            )
        if data.cover_letter_id is not None:
            self._require_cover_letter_for_application(
                db, user_id, data.cover_letter_id, job_id, resume_profile_id
            )

        application = Application(
            user_id=user_id,
            job_id=job_id,
            resume_profile_id=resume_profile_id,
            cover_letter_id=data.cover_letter_id,
            job_recommendation_id=data.job_recommendation_id,
            status=data.status,
            source=source,
            notes=data.notes,
            company_response=data.company_response,
            interview_date=data.interview_date,
            follow_up_date=data.follow_up_date,
            last_status_change_at=datetime.now(timezone.utc),
        )
        return self.application_repository.create(db, application)

    def get_application(
        self, db: Session, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> Application:
        application = self.application_repository.get_by_id(
            db, application_id, user_id
        )
        if application is None:
            raise ApplicationNotFoundError("Application not found")
        return application

    def list_applications(
        self,
        db: Session,
        user_id: uuid.UUID,
        filters: ApplicationFilter | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Application]:
        return self.application_repository.list(
            db, user_id, filters=filters, skip=skip, limit=limit
        )

    def update_application(
        self,
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        data: ApplicationUpdate,
    ) -> Application:
        application = self.get_application(db, user_id, application_id)
        update_fields = data.model_fields_set

        if "cover_letter_id" in update_fields:
            if data.cover_letter_id is not None:
                self._require_cover_letter_for_application(
                    db,
                    user_id,
                    data.cover_letter_id,
                    application.job_id,
                    application.resume_profile_id,
                )
            application.cover_letter_id = data.cover_letter_id

        if "job_recommendation_id" in update_fields:
            if data.job_recommendation_id is not None:
                recommendation = self._require_recommendation(
                    db, user_id, data.job_recommendation_id
                )
                self._validate_recommendation_links(
                    recommendation,
                    application.job_id,
                    application.resume_profile_id,
                )
            application.job_recommendation_id = data.job_recommendation_id

        for field in (
            "notes",
            "company_response",
            "interview_date",
            "follow_up_date",
        ):
            if field in update_fields:
                setattr(application, field, getattr(data, field))

        return self.application_repository.update(db, application)

    def update_status(
        self,
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        status: ApplicationStatus,
    ) -> Application:
        application = self.get_application(db, user_id, application_id)
        self.transition_service.validate_transition(
            application.status, status
        )
        if application.status == status:
            return application

        application.status = status
        self._apply_status_timestamps(application, status)
        return self.application_repository.update(db, application)

    def delete_application(
        self, db: Session, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> Application | None:
        application = self.application_repository.get_by_id(
            db, application_id, user_id
        )
        if application is None:
            return None
        return self.application_repository.soft_delete(db, application)

    # --- resource validation ---------------------------------------------

    def _require_live_job(self, db, job_id):
        job = self.job_repository.get_by_id(db, job_id)
        if job is None:
            raise ApplicationResourceNotFoundError("Job not found")
        return job

    def _require_live_profile_and_resume(self, db, user_id, resume_profile_id):
        profile = self.resume_profile_repository.get_by_id(
            db, resume_profile_id, user_id
        )
        if profile is None:
            raise ApplicationResourceNotFoundError("Resume profile not found")
        if self.resume_repository.get_by_id(db, profile.resume_id, user_id) is None:
            raise ApplicationResourceNotFoundError("Resume not found")
        return profile

    def _require_cover_letter_for_application(
        self, db, user_id, cover_letter_id, job_id, resume_profile_id
    ):
        cover_letter = self.cover_letter_repository.get_by_id(
            db, cover_letter_id, user_id
        )
        if cover_letter is None:
            raise ApplicationResourceNotFoundError("Cover letter not found")
        if (
            cover_letter.job_id != job_id
            or cover_letter.resume_profile_id != resume_profile_id
        ):
            raise ApplicationResourceMismatchError(
                "Cover letter does not belong to the application job/profile"
            )
        return cover_letter

    def _require_recommendation(self, db, user_id, recommendation_id):
        recommendation = self.job_recommendation_repository.get_by_id(
            db, recommendation_id, user_id
        )
        if recommendation is None:
            raise ApplicationResourceNotFoundError("Recommendation not found")
        return recommendation

    @staticmethod
    def _validate_recommendation_links(
        recommendation, job_id, resume_profile_id
    ) -> None:
        if (
            recommendation.job_id != job_id
            or recommendation.resume_profile_id != resume_profile_id
        ):
            raise ApplicationResourceMismatchError(
                "Recommendation does not belong to the application job/profile"
            )

    @staticmethod
    def _apply_status_timestamps(
        application: Application, status: ApplicationStatus
    ) -> None:
        now = datetime.now(timezone.utc)
        application.last_status_change_at = now
        if status == ApplicationStatus.APPLIED and application.applied_at is None:
            application.applied_at = now
        elif status == ApplicationStatus.OFFER and application.offer_date is None:
            application.offer_date = now
        elif (
            status == ApplicationStatus.REJECTED
            and application.rejection_date is None
        ):
            application.rejection_date = now


__all__ = [
    "ApplicationService",
    "ApplicationNotFoundError",
    "ApplicationResourceNotFoundError",
    "ApplicationResourceMismatchError",
    "InvalidApplicationDataError",
    "InvalidApplicationStatusTransitionError",
    "InvalidInitialApplicationStatusError",
]
