import json
import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.application import ApplicationSource, ApplicationStatus
from app.models.interview_preparation import (
    InterviewDifficulty,
    InterviewPreparationStatus,
)
from app.services.ai.base_interview_client import InterviewPreparationAIError
from app.services.interview_preparation_service import (
    InterviewPreparationApplicationNotFoundError,
    InterviewPreparationApplicationNotReadyError,
    InterviewPreparationNotFoundError,
    InterviewPreparationService,
)


def good_ai_payload(summary="Prepare for backend interview"):
    return json.dumps(
        {
            "summary": summary,
            "strengths": [
                {"title": "Python", "reason": "Listed on the profile."}
            ],
            "weaknesses": [
                {
                    "title": "System design depth",
                    "reason": "Job mentions scalable services.",
                }
            ],
            "technical_questions": [
                {
                    "question": "How would you design an API rate limiter?",
                    "reason": "The role mentions backend APIs.",
                    "difficulty": "medium",
                }
            ],
            "behavioral_questions": [
                {
                    "question": "Tell me about a difficult debugging session.",
                    "reason": "Backend work often involves production issues.",
                    "difficulty": "medium",
                }
            ],
            "company_questions": [
                {
                    "question": "How does the team define reliability?",
                    "reason": "The posting references uptime.",
                    "difficulty": "easy",
                }
            ],
            "study_topics": [
                {
                    "topic": "SQL query planning",
                    "reason": "The job asks for PostgreSQL.",
                    "priority": "medium",
                }
            ],
            "interview_tips": [
                {
                    "tip": "Anchor answers in supplied resume projects.",
                    "reason": "Avoid inventing examples.",
                }
            ],
            "estimated_difficulty": "medium",
        }
    )


class FakeInterviewClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate_interview_preparation(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeApplicationRepository:
    def __init__(self, applications):
        self.applications = applications

    def get_by_id(self, db, application_id, user_id):
        application = self.applications.get(application_id)
        if (
            application is None
            or application.user_id != user_id
            or application.deleted_at is not None
        ):
            return None
        return application


class FakePreparationRepository:
    def __init__(self):
        self.rows = {}
        self.created = 0
        self.updated = 0

    def create(self, db, preparation):
        self.created += 1
        if preparation.id is None:
            preparation.id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        preparation.created_at = now
        preparation.updated_at = now
        preparation.deleted_at = None
        self.rows[(preparation.application_id, preparation.user_id)] = (
            preparation
        )
        return preparation

    def update(self, db, preparation):
        self.updated += 1
        preparation.updated_at = datetime.now(timezone.utc)
        return preparation

    def get_by_application(self, db, application_id, user_id):
        preparation = self.rows.get((application_id, user_id))
        if preparation is None or preparation.deleted_at is not None:
            return None
        return preparation

    def get_by_id(self, db, preparation_id, user_id):
        for preparation in self.rows.values():
            if (
                preparation.id == preparation_id
                and preparation.user_id == user_id
                and preparation.deleted_at is None
            ):
                return preparation
        return None

    def list_by_user(self, db, user_id, skip=0, limit=50):
        rows = [
            prep
            for prep in self.rows.values()
            if prep.user_id == user_id and prep.deleted_at is None
        ]
        return rows[skip : skip + limit]

    def soft_delete(self, db, preparation):
        preparation.deleted_at = datetime.now(timezone.utc)
        return preparation


class FakeJobMatchRepository:
    def __init__(self, match=None):
        self.match = match

    def get_by_profile_job(self, db, resume_profile_id, job_id, user_id):
        return self.match


def row(**kwargs):
    kwargs.setdefault("deleted_at", None)
    return SimpleNamespace(**kwargs)


def make_application(user_id, status=ApplicationStatus.READY, deleted=False):
    company = row(name="Acme")
    job = row(
        id=uuid.uuid4(),
        title="Backend Engineer",
        company=company,
        location="Berlin",
        remote_type="hybrid",
        employment_type="full_time",
        description="Build APIs with Python and PostgreSQL.",
        requirements="Python, SQLAlchemy, PostgreSQL",
    )
    profile = row(
        id=uuid.uuid4(),
        full_name="Ada Candidate",
        location="Berlin",
        summary="Backend engineer.",
        skills=["Python", "PostgreSQL"],
        work_experience=[{"title": "Backend Engineer"}],
        education=[],
        projects=[],
        certifications=[],
        languages=["English"],
    )
    cover_letter = row(
        content="I am excited about backend systems.",
        language="en",
        tone="professional",
        generation_status=row(value="completed"),
    )
    return row(
        id=uuid.uuid4(),
        user_id=user_id,
        status=status,
        source=ApplicationSource.MANUAL,
        job_id=job.id,
        resume_profile_id=profile.id,
        job=job,
        resume_profile=profile,
        cover_letter=cover_letter,
        applied_at=None,
        interview_date=None,
        company_response=None,
        notes=None,
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )


def make_service(application, client):
    prep_repository = FakePreparationRepository()
    service = InterviewPreparationService(
        interview_preparation_repository=prep_repository,
        application_repository=FakeApplicationRepository(
            {application.id: application}
        ),
        job_match_repository=FakeJobMatchRepository(),
        interview_client=client,
    )
    return service, prep_repository


class InterviewPreparationServiceTests(unittest.TestCase):
    def test_create_interview_preparation(self):
        user_id = uuid.uuid4()
        application = make_application(user_id)
        service, repository = make_service(
            application, FakeInterviewClient([good_ai_payload()])
        )

        preparation = service.generate(None, user_id, application.id)

        self.assertEqual(
            preparation.generation_status,
            InterviewPreparationStatus.COMPLETED,
        )
        self.assertEqual(
            preparation.estimated_difficulty, InterviewDifficulty.MEDIUM
        )
        self.assertEqual(repository.created, 1)
        self.assertEqual(repository.updated, 0)
        self.assertIsInstance(preparation.technical_questions[0], dict)

    def test_regenerate_updates_existing_row(self):
        user_id = uuid.uuid4()
        application = make_application(user_id)
        service, repository = make_service(
            application,
            FakeInterviewClient(
                [
                    good_ai_payload("First"),
                    good_ai_payload("Second"),
                ]
            ),
        )

        first = service.generate(None, user_id, application.id)
        second = service.generate(None, user_id, application.id)

        self.assertEqual(first.id, second.id)
        self.assertEqual(second.summary, "Second")
        self.assertEqual(repository.created, 1)
        self.assertEqual(repository.updated, 1)

    def test_draft_application_rejected(self):
        user_id = uuid.uuid4()
        application = make_application(user_id, status=ApplicationStatus.DRAFT)
        service, _ = make_service(
            application, FakeInterviewClient([good_ai_payload()])
        )

        with self.assertRaises(InterviewPreparationApplicationNotReadyError):
            service.generate(None, user_id, application.id)

    def test_deleted_application_rejected(self):
        user_id = uuid.uuid4()
        application = make_application(user_id, deleted=True)
        service, _ = make_service(
            application, FakeInterviewClient([good_ai_payload()])
        )

        with self.assertRaises(InterviewPreparationApplicationNotFoundError):
            service.generate(None, user_id, application.id)

    def test_cross_user_application_returns_not_found(self):
        user_id = uuid.uuid4()
        application = make_application(user_id)
        service, _ = make_service(
            application, FakeInterviewClient([good_ai_payload()])
        )

        with self.assertRaises(InterviewPreparationApplicationNotFoundError):
            service.generate(None, uuid.uuid4(), application.id)

    def test_provider_failure_is_stored_as_failed(self):
        user_id = uuid.uuid4()
        application = make_application(user_id)
        service, _ = make_service(
            application,
            FakeInterviewClient(
                [InterviewPreparationAIError("provider unavailable")]
            ),
        )

        preparation = service.generate(None, user_id, application.id)

        self.assertEqual(
            preparation.generation_status, InterviewPreparationStatus.FAILED
        )
        self.assertIn("provider unavailable", preparation.generation_error)

    def test_invalid_ai_json_is_stored_as_failed(self):
        user_id = uuid.uuid4()
        application = make_application(user_id)
        service, _ = make_service(
            application, FakeInterviewClient(['{"summary": ""}'])
        )

        preparation = service.generate(None, user_id, application.id)

        self.assertEqual(
            preparation.generation_status, InterviewPreparationStatus.FAILED
        )
        self.assertIsNone(preparation.summary)
        self.assertEqual(preparation.raw_ai_response, '{"summary": ""}')

    def test_owner_scoped_get_list_and_soft_delete(self):
        user_id = uuid.uuid4()
        application = make_application(user_id)
        service, _ = make_service(
            application, FakeInterviewClient([good_ai_payload()])
        )
        preparation = service.generate(None, user_id, application.id)

        self.assertEqual(
            service.get_by_application(None, user_id, application.id).id,
            preparation.id,
        )
        self.assertEqual(
            service.list_by_user(None, user_id)[0].id, preparation.id
        )
        with self.assertRaises(InterviewPreparationApplicationNotFoundError):
            service.get_by_application(None, uuid.uuid4(), application.id)

        service.delete(None, user_id, preparation.id)

        with self.assertRaises(InterviewPreparationNotFoundError):
            service.get_by_application(None, user_id, application.id)
        self.assertEqual(service.list_by_user(None, user_id), [])


if __name__ == "__main__":
    unittest.main()
