import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.application import ApplicationSource, ApplicationStatus
from app.repositories.application_repository import ApplicationRepository
from app.schemas.application import ApplicationFilter


class CapturingSession:
    def __init__(self):
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))


class ApplicationRepositoryTests(unittest.TestCase):
    def test_list_applies_filters_and_pagination(self):
        db = CapturingSession()
        repository = ApplicationRepository()

        repository.list(
            db,
            uuid.uuid4(),
            filters=ApplicationFilter(
                status=ApplicationStatus.APPLIED,
                company="OpenAI",
                source=ApplicationSource.RECOMMENDATION,
                date_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                date_to=datetime(2026, 2, 1, tzinfo=timezone.utc),
            ),
            skip=10,
            limit=20,
        )

        sql = str(
            db.statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": False},
            )
        )
        self.assertIn("applications.status = ", sql)
        self.assertIn("applications.source = ", sql)
        self.assertIn("applications.created_at >=", sql)
        self.assertIn("applications.created_at <=", sql)
        self.assertIn("JOIN jobs", sql)
        self.assertIn("JOIN companies", sql)
        self.assertIn("LIMIT", sql)
        self.assertIn("OFFSET", sql)


if __name__ == "__main__":
    unittest.main()
