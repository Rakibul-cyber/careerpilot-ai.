import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.repositories.job_embedding_repository import JobEmbeddingRepository


class CapturingSession:
    def __init__(self):
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return SimpleNamespace(all=lambda: [])


class JobEmbeddingRepositoryTests(unittest.TestCase):
    def test_semantic_search_requires_completed_embeddings(self):
        db = CapturingSession()
        repository = JobEmbeddingRepository()

        repository.semantic_search(db, [0.0] * 1536, limit=10)

        sql = str(
            db.statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": False},
            )
        )
        self.assertIn("jobs.deleted_at IS NULL", sql)
        self.assertIn("jobs.status = ", sql)
        self.assertIn("jobs.embedding IS NOT NULL", sql)
        self.assertIn("jobs.embedding_status = ", sql)


if __name__ == "__main__":
    unittest.main()
