import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.resume_profile import ResumeParseStatus
from app.services.job_recommendation_service import (
    JobRecommendationNotFoundError,
    JobRecommendationService,
    ResumeProfileNotCompletedError,
    ResumeProfileNotFoundError,
)


class FakeProfileRepository:
    def __init__(self, profiles):
        self.profiles = profiles

    def get_by_id(self, db, profile_id, user_id):
        profile = self.profiles.get(profile_id)
        if profile is None or profile.user_id != user_id:
            return None
        return profile


class FakeRecommendationRepository:
    def __init__(self):
        self.rows = {}
        self.created = 0
        self.updated = 0

    def create(self, db, recommendation):
        self.created += 1
        if recommendation.id is None:
            recommendation.id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        recommendation.created_at = now
        recommendation.updated_at = now
        self.rows[
            (
                recommendation.resume_profile_id,
                recommendation.job_id,
                recommendation.user_id,
            )
        ] = recommendation
        return recommendation

    def update(self, db, recommendation):
        self.updated += 1
        recommendation.updated_at = datetime.now(timezone.utc)
        return recommendation

    def get_by_profile_job(self, db, resume_profile_id, job_id, user_id):
        return self.rows.get((resume_profile_id, job_id, user_id))

    def get_by_id(self, db, recommendation_id, user_id):
        for recommendation in self.rows.values():
            if (
                recommendation.id == recommendation_id
                and recommendation.user_id == user_id
            ):
                return recommendation
        return None

    def list_by_profile(self, db, resume_profile_id, user_id, skip=0, limit=50):
        rows = [
            row
            for row in self.rows.values()
            if row.resume_profile_id == resume_profile_id
            and row.user_id == user_id
        ]
        rows.sort(key=lambda row: row.final_score, reverse=True)
        return rows[skip : skip + limit]


class FakeSemanticSearchService:
    def __init__(self, hits):
        self.hits = hits
        self.queries = []

    def search(self, db, query, limit=20):
        self.queries.append((query, limit))
        return self.hits[:limit]


class FakeJobMatchService:
    def __init__(self, scores):
        self.scores = scores
        self.calls = []
        self.matches = {}

    def match(self, db, user_id, resume_profile_id, job_id):
        self.calls.append((user_id, resume_profile_id, job_id))
        key = (user_id, resume_profile_id, job_id)
        match = self.matches.get(key)
        if match is None:
            match = SimpleNamespace(
                id=uuid.uuid4(),
                overall_score=self.scores[job_id],
                match_reasons=["Strong Python overlap."],
                risk_flags=[],
            )
            self.matches[key] = match
        else:
            match.overall_score = self.scores[job_id]
        return match


def make_profile(user_id, parse_status=ResumeParseStatus.COMPLETED):
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        parse_status=parse_status,
        summary="Backend engineer building FastAPI services.",
        skills=["Python", "SQLAlchemy", "PostgreSQL"],
        work_experience=[{"title": "Backend Engineer"}],
        location="Berlin",
    )


def make_service(profile, hits, scores):
    recommendation_repository = FakeRecommendationRepository()
    service = JobRecommendationService(
        resume_profile_repository=FakeProfileRepository({profile.id: profile}),
        job_recommendation_repository=recommendation_repository,
        semantic_search_service=FakeSemanticSearchService(hits),
        job_match_service=FakeJobMatchService(scores),
    )
    return service, recommendation_repository


class JobRecommendationServiceTests(unittest.TestCase):
    def test_generate_recommendations_ranked_and_upserts_on_rerun(self):
        user_id = uuid.uuid4()
        profile = make_profile(user_id)
        job_a = SimpleNamespace(id=uuid.uuid4())
        job_b = SimpleNamespace(id=uuid.uuid4())
        hits = [(job_a, 0.25), (job_b, 0.9)]
        scores = {job_a.id: 90.0, job_b.id: 50.0}
        service, recommendation_repository = make_service(profile, hits, scores)

        first = service.recommend(None, user_id, profile.id, limit=10)
        second = service.recommend(None, user_id, profile.id, limit=10)

        self.assertEqual([row.job_id for row in first], [job_b.id, job_a.id])
        self.assertEqual([row.job_id for row in second], [job_b.id, job_a.id])
        self.assertEqual(recommendation_repository.created, 2)
        self.assertEqual(recommendation_repository.updated, 2)
        self.assertEqual(len(recommendation_repository.rows), 2)
        self.assertEqual(first[0].final_score, 66.0)
        self.assertEqual(first[1].final_score, 64.0)
        self.assertGreater(second[0].final_score, second[1].final_score)
        self.assertIsNotNone(second[0].job_match_id)
        self.assertEqual(len(service.job_match_service.calls), 4)

    def test_profile_must_be_completed(self):
        user_id = uuid.uuid4()
        profile = make_profile(user_id, ResumeParseStatus.PENDING)
        service, _ = make_service(profile, [], {})

        with self.assertRaises(ResumeProfileNotCompletedError):
            service.recommend(None, user_id, profile.id)

    def test_cross_user_profile_returns_not_found(self):
        owner_id = uuid.uuid4()
        other_user_id = uuid.uuid4()
        profile = make_profile(owner_id)
        service, _ = make_service(profile, [], {})

        with self.assertRaises(ResumeProfileNotFoundError):
            service.recommend(None, other_user_id, profile.id)

    def test_get_and_list_are_owner_scoped(self):
        user_id = uuid.uuid4()
        other_user_id = uuid.uuid4()
        profile = make_profile(user_id)
        job = SimpleNamespace(id=uuid.uuid4())
        service, _ = make_service(profile, [(job, 1.0)], {job.id: 75.0})
        recommendation = service.recommend(None, user_id, profile.id)[0]

        self.assertEqual(
            service.get_recommendation(None, user_id, recommendation.id).id,
            recommendation.id,
        )
        self.assertEqual(
            service.list_recommendations(None, user_id, profile.id)[0].id,
            recommendation.id,
        )
        with self.assertRaises(JobRecommendationNotFoundError):
            service.get_recommendation(None, other_user_id, recommendation.id)
        with self.assertRaises(ResumeProfileNotFoundError):
            service.list_recommendations(None, other_user_id, profile.id)


if __name__ == "__main__":
    unittest.main()
