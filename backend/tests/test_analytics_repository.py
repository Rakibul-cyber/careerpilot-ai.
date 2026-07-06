import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.job import JobEmbeddingStatus
from app.repositories.analytics_repository import AnalyticsRepository


class CapturingSession:
    def __init__(self):
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        return SimpleNamespace(scalar_one=lambda: 0)


def compile_sql(statement):
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": False},
        )
    )


class AnalyticsRepositoryTests(unittest.TestCase):
    def test_application_count_is_user_scoped_live_and_date_filtered(self):
        db = CapturingSession()
        repo = AnalyticsRepository()

        repo.application_count(
            db,
            uuid.uuid4(),
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 2, 1, tzinfo=timezone.utc),
        )

        sql = compile_sql(db.statements[0])
        self.assertIn("applications.user_id =", sql)
        self.assertIn("applications.deleted_at IS NULL", sql)
        self.assertIn("applications.created_at >=", sql)
        self.assertIn("applications.created_at <=", sql)

    def test_job_embedding_count_scopes_to_user_interaction_subqueries(self):
        db = CapturingSession()
        repo = AnalyticsRepository()

        repo._job_embedding_count(
            db,
            uuid.uuid4(),
            None,
            None,
            JobEmbeddingStatus.COMPLETED,
        )

        sql = compile_sql(db.statements[0])
        self.assertIn("applications.user_id =", sql)
        self.assertIn("job_matches.user_id =", sql)
        self.assertIn("job_recommendations.user_id =", sql)
        self.assertIn("jobs.deleted_at IS NULL", sql)
        self.assertIn("jobs.embedding_status =", sql)


if __name__ == "__main__":
    unittest.main()
