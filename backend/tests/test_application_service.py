import sys
import unittest
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain.application.transitions import (
    ApplicationStatusTransitionService,
    InvalidApplicationStatusTransitionError,
)
from app.models.application import ApplicationSource, ApplicationStatus
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.services.application_service import (
    ApplicationNotFoundError,
    ApplicationResourceNotFoundError,
    ApplicationService,
)


class FakeApplicationRepository:
    def __init__(self):
        self.rows = {}

    def create(self, db, application):
        application.id = uuid.uuid4()
        now = datetime.now(UTC)
        application.created_at = now
        application.updated_at = now
        self.rows[application.id] = application
        return application

    def update(self, db, application):
        application.updated_at = datetime.now(UTC)
        return application

    def get_by_id(self, db, application_id, user_id):
        application = self.rows.get(application_id)
        if (
            application is None
            or application.user_id != user_id
            or application.deleted_at is not None
        ):
            return None
        return application

    def list(self, db, user_id, filters=None, skip=0, limit=50):
        rows = [
            row
            for row in self.rows.values()
            if row.user_id == user_id and row.deleted_at is None
        ]
        return rows[skip : skip + limit]

    def soft_delete(self, db, application):
        application.deleted_at = datetime.now(UTC)
        return application


class FakeScopedRepository:
    def __init__(self, rows):
        self.rows = rows

    def get_by_id(self, db, row_id, user_id=None):
        row = self.rows.get(row_id)
        if row is None:
            return None
        if user_id is not None and getattr(row, "user_id", user_id) != user_id:
            return None
        if getattr(row, "deleted_at", None) is not None:
            return None
        return row


def row(**values):
    values.setdefault("deleted_at", None)
    return SimpleNamespace(**values)


def make_service():
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    cover_letter_id = uuid.uuid4()
    recommendation_id = uuid.uuid4()

    profile = row(id=profile_id, user_id=user_id, resume_id=resume_id)
    resume = row(id=resume_id, user_id=user_id)
    cover_letter = row(
        id=cover_letter_id,
        user_id=user_id,
        job_id=job_id,
        resume_profile_id=profile_id,
    )
    recommendation = row(
        id=recommendation_id,
        user_id=user_id,
        job_id=job_id,
        resume_profile_id=profile_id,
    )

    application_repository = FakeApplicationRepository()
    service = ApplicationService(
        application_repository=application_repository,
        job_repository=FakeScopedRepository({job_id: row(id=job_id)}),
        resume_profile_repository=FakeScopedRepository({profile_id: profile}),
        resume_repository=FakeScopedRepository({resume_id: resume}),
        cover_letter_repository=FakeScopedRepository({cover_letter_id: cover_letter}),
        job_recommendation_repository=FakeScopedRepository(
            {recommendation_id: recommendation}
        ),
        transition_service=ApplicationStatusTransitionService(),
    )
    return SimpleNamespace(
        service=service,
        repository=application_repository,
        user_id=user_id,
        job_id=job_id,
        resume_id=resume_id,
        profile_id=profile_id,
        cover_letter_id=cover_letter_id,
        recommendation_id=recommendation_id,
    )


class ApplicationServiceTests(unittest.TestCase):
    def test_create_draft_application(self):
        ctx = make_service()

        application = ctx.service.create_application(
            None,
            ctx.user_id,
            ApplicationCreate(
                job_id=ctx.job_id,
                resume_profile_id=ctx.profile_id,
                cover_letter_id=ctx.cover_letter_id,
                notes="Promising role",
            ),
        )

        self.assertEqual(application.status, ApplicationStatus.DRAFT)
        self.assertEqual(application.source, ApplicationSource.MANUAL)
        self.assertEqual(application.notes, "Promising role")
        self.assertIsNotNone(application.last_status_change_at)

    def test_create_from_recommendation_derives_job_profile_and_source(self):
        ctx = make_service()

        application = ctx.service.create_application(
            None,
            ctx.user_id,
            ApplicationCreate(job_recommendation_id=ctx.recommendation_id),
        )

        self.assertEqual(application.job_id, ctx.job_id)
        self.assertEqual(application.resume_profile_id, ctx.profile_id)
        self.assertEqual(application.source, ApplicationSource.RECOMMENDATION)

    def test_cross_user_resource_returns_not_found(self):
        ctx = make_service()

        with self.assertRaises(ApplicationResourceNotFoundError):
            ctx.service.create_application(
                None,
                uuid.uuid4(),
                ApplicationCreate(
                    job_id=ctx.job_id,
                    resume_profile_id=ctx.profile_id,
                ),
            )

    def test_deleted_resource_is_rejected(self):
        ctx = make_service()
        ctx.service.job_repository.rows[ctx.job_id].deleted_at = datetime.now(UTC)

        with self.assertRaises(ApplicationResourceNotFoundError):
            ctx.service.create_application(
                None,
                ctx.user_id,
                ApplicationCreate(
                    job_id=ctx.job_id,
                    resume_profile_id=ctx.profile_id,
                ),
            )

    def test_valid_status_transition_sets_applied_timestamp(self):
        ctx = make_service()
        application = ctx.service.create_application(
            None,
            ctx.user_id,
            ApplicationCreate(
                job_id=ctx.job_id,
                resume_profile_id=ctx.profile_id,
                status=ApplicationStatus.READY,
            ),
        )

        updated = ctx.service.update_status(
            None, ctx.user_id, application.id, ApplicationStatus.APPLIED
        )

        self.assertEqual(updated.status, ApplicationStatus.APPLIED)
        self.assertIsNotNone(updated.applied_at)
        self.assertIsNotNone(updated.last_status_change_at)

    def test_offer_and_rejection_timestamps_are_auto_populated(self):
        ctx = make_service()
        application = ctx.service.create_application(
            None,
            ctx.user_id,
            ApplicationCreate(
                job_id=ctx.job_id,
                resume_profile_id=ctx.profile_id,
                status=ApplicationStatus.READY,
            ),
        )
        application.status = ApplicationStatus.FINAL_INTERVIEW

        offered = ctx.service.update_status(
            None, ctx.user_id, application.id, ApplicationStatus.OFFER
        )
        self.assertIsNotNone(offered.offer_date)

        rejected = ctx.service.update_status(
            None, ctx.user_id, application.id, ApplicationStatus.REJECTED
        )
        self.assertIsNotNone(rejected.rejection_date)

    def test_invalid_status_transition_is_rejected(self):
        ctx = make_service()
        application = ctx.service.create_application(
            None,
            ctx.user_id,
            ApplicationCreate(job_id=ctx.job_id, resume_profile_id=ctx.profile_id),
        )

        with self.assertRaises(InvalidApplicationStatusTransitionError):
            ctx.service.update_status(
                None, ctx.user_id, application.id, ApplicationStatus.OFFER
            )

    def test_patch_notes_and_follow_up_date(self):
        ctx = make_service()
        application = ctx.service.create_application(
            None,
            ctx.user_id,
            ApplicationCreate(job_id=ctx.job_id, resume_profile_id=ctx.profile_id),
        )
        follow_up = datetime.now(UTC)

        updated = ctx.service.update_application(
            None,
            ctx.user_id,
            application.id,
            ApplicationUpdate(notes="Send follow-up", follow_up_date=follow_up),
        )

        self.assertEqual(updated.notes, "Send follow-up")
        self.assertEqual(updated.follow_up_date, follow_up)

    def test_soft_delete_hides_application(self):
        ctx = make_service()
        application = ctx.service.create_application(
            None,
            ctx.user_id,
            ApplicationCreate(job_id=ctx.job_id, resume_profile_id=ctx.profile_id),
        )

        ctx.service.delete_application(None, ctx.user_id, application.id)

        with self.assertRaises(ApplicationNotFoundError):
            ctx.service.get_application(None, ctx.user_id, application.id)


if __name__ == "__main__":
    unittest.main()
