import sys
import unittest
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.application import ApplicationStatus
from app.services.analytics_service import AnalyticsService


class FakeAnalyticsRepository:
    def __init__(self):
        self.calls = []
        self.empty = False

    def application_count(self, db, user_id, start_date=None, end_date=None):
        self.calls.append(("application_count", user_id, start_date, end_date))
        return 0 if self.empty else 4

    def application_counts_by_status(self, db, user_id, start_date=None, end_date=None):
        return [] if self.empty else [("applied", 2), ("offer", 1), ("rejected", 1)]

    def application_counts_by_source(self, db, user_id, start_date=None, end_date=None):
        return [] if self.empty else [("manual", 3), ("recommendation", 1)]

    def active_application_count(self, db, user_id, start_date=None, end_date=None):
        return 0 if self.empty else 3

    def status_group_count(self, db, user_id, statuses, start_date=None, end_date=None):
        if self.empty:
            return 0
        if ApplicationStatus.VIEWED in statuses:
            return 3
        if ApplicationStatus.REJECTED in statuses:
            return 1
        if ApplicationStatus.OFFER in statuses:
            return 1
        if ApplicationStatus.PHONE_SCREEN in statuses:
            return 1
        return 0

    def upcoming_followup_count(self, db, user_id):
        return 0 if self.empty else 2

    def due_followup_count(self, db, user_id):
        return 0 if self.empty else 1

    def applications_over_time(self, db, user_id, start_date=None, end_date=None):
        return [] if self.empty else [(date(2026, 7, 1), 2), (date(2026, 7, 2), 2)]

    def average_match_scores(self, db, user_id, start_date=None, end_date=None):
        if self.empty:
            return {
                "overall": None,
                "skill": None,
                "title": None,
                "location": None,
                "experience": None,
            }
        return {
            "overall": 82.5,
            "skill": 40.0,
            "title": 15.0,
            "location": 10.0,
            "experience": 12.5,
        }

    def top_recommended_jobs(self, db, user_id, limit, start_date=None, end_date=None):
        if self.empty:
            return []
        return [
            {
                "job_id": uuid.uuid4(),
                "title": "Backend Engineer",
                "company": "Acme",
                "final_score": 91.0,
                "semantic_score": 0.9,
                "match_score": 92.0,
            }
        ]

    def recent_activity(self, db, user_id, limit, start_date=None, end_date=None):
        if self.empty:
            return []
        return [
            {
                "type": "application",
                "id": uuid.uuid4(),
                "occurred_at": datetime.now(UTC),
                "label": "Application applied",
            }
        ]

    def ranked_matches(
        self, db, user_id, descending, limit, start_date=None, end_date=None
    ):
        if self.empty:
            return []
        return [
            {
                "job_id": uuid.uuid4(),
                "title": "Backend Engineer",
                "company": "Acme",
                "overall_score": 88.0 if descending else 42.0,
                "skill_score": 45.0,
                "title_score": 18.0,
                "location_score": 10.0,
                "experience_score": 15.0,
            }
        ]

    def common_missing_skills(self, db, user_id, limit, start_date=None, end_date=None):
        return [] if self.empty else [("Kubernetes", 3), ("Terraform", 2)]

    def ai_usage_counts(self, db, user_id, start_date=None, end_date=None):
        if self.empty:
            return {
                "resume_profiles": 0,
                "cover_letters": 0,
                "interview_preparations": 0,
                "job_embeddings": 0,
                "recommendations": 0,
                "failed_resume_parses": 0,
                "failed_cover_letters": 0,
                "failed_interview_preparations": 0,
                "failed_job_embeddings": 0,
            }
        return {
            "resume_profiles": 5,
            "cover_letters": 4,
            "interview_preparations": 2,
            "job_embeddings": 7,
            "recommendations": 9,
            "failed_resume_parses": 1,
            "failed_cover_letters": 1,
            "failed_interview_preparations": 1,
            "failed_job_embeddings": 2,
        }


class AnalyticsServiceTests(unittest.TestCase):
    def test_overview_counts_correct_and_date_filters_passed(self):
        repo = FakeAnalyticsRepository()
        service = AnalyticsService(repo)
        user_id = uuid.uuid4()
        start = datetime(2026, 7, 1, tzinfo=UTC)
        end = datetime(2026, 7, 31, tzinfo=UTC)

        overview = service.overview(None, user_id, start, end, limit=5)

        self.assertEqual(overview.total_applications, 4)
        self.assertEqual(overview.active_applications, 3)
        self.assertEqual(overview.offers, 1)
        self.assertEqual(overview.rejections, 1)
        self.assertEqual(overview.interviews, 1)
        self.assertEqual(overview.upcoming_followups, 2)
        self.assertEqual(overview.average_match_score, 82.5)
        self.assertEqual(repo.calls[0], ("application_count", user_id, start, end))

    def test_application_rates_and_buckets(self):
        service = AnalyticsService(FakeAnalyticsRepository())

        analytics = service.applications(None, uuid.uuid4())

        self.assertEqual(analytics.status_counts[0].key, "applied")
        self.assertEqual(analytics.source_counts[1].key, "recommendation")
        self.assertEqual(analytics.response_rate, 0.75)
        self.assertEqual(analytics.offer_rate, 0.25)
        self.assertEqual(analytics.rejection_rate, 0.25)
        self.assertEqual(analytics.interview_rate, 0.25)
        self.assertEqual(analytics.follow_up_due_count, 1)

    def test_match_analytics_averages_and_common_missing_skills(self):
        service = AnalyticsService(FakeAnalyticsRepository())

        analytics = service.matches(None, uuid.uuid4(), limit=2)

        self.assertEqual(analytics.average_overall_score, 82.5)
        self.assertEqual(analytics.best_matches[0].overall_score, 88.0)
        self.assertEqual(analytics.weak_matches[0].overall_score, 42.0)
        self.assertEqual(analytics.common_missing_skills[0].skill, "Kubernetes")
        self.assertEqual(analytics.common_missing_skills[0].count, 3)

    def test_ai_usage_success_and_failure_counts(self):
        service = AnalyticsService(FakeAnalyticsRepository())

        analytics = service.ai_usage(None, uuid.uuid4())

        self.assertEqual(analytics.resume_profiles, 5)
        self.assertEqual(analytics.cover_letters, 4)
        self.assertEqual(analytics.interview_preparations, 2)
        self.assertEqual(analytics.job_embeddings, 7)
        self.assertEqual(analytics.recommendations, 9)
        self.assertEqual(analytics.failed_resume_parses, 1)
        self.assertEqual(analytics.failed_cover_letters, 1)
        self.assertEqual(analytics.failed_interview_preparations, 1)
        self.assertEqual(analytics.failed_job_embeddings, 2)

    def test_empty_user_returns_zeroes_and_empty_lists(self):
        repo = FakeAnalyticsRepository()
        repo.empty = True
        service = AnalyticsService(repo)

        overview = service.overview(None, uuid.uuid4())
        applications = service.applications(None, uuid.uuid4())
        matches = service.matches(None, uuid.uuid4())
        usage = service.ai_usage(None, uuid.uuid4())

        self.assertEqual(overview.total_applications, 0)
        self.assertEqual(overview.top_recommended_jobs, [])
        self.assertEqual(applications.response_rate, 0.0)
        self.assertEqual(applications.applications_over_time, [])
        self.assertIsNone(matches.average_overall_score)
        self.assertEqual(matches.common_missing_skills, [])
        self.assertEqual(usage.recommendations, 0)


if __name__ == "__main__":
    unittest.main()
