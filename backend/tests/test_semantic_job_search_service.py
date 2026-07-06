import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.semantic_job_search_service import SemanticJobSearchService


class FakeEmbeddingClient:
    model_name = "fake-embedding"

    def embed_text(self, text):
        return [0.0] * 1536


class FakeJobEmbeddingRepository:
    def semantic_search(self, db, query_vector, limit):
        return [
            (SimpleNamespace(id="too_far"), 1.2),
            (SimpleNamespace(id="exact"), 0.0),
        ]


class SemanticJobSearchServiceTests(unittest.TestCase):
    def test_similarity_scores_are_clamped_to_zero_to_one(self):
        service = SemanticJobSearchService(
            job_embedding_repository=FakeJobEmbeddingRepository(),
            embedding_client=FakeEmbeddingClient(),
        )

        results = service.search(None, "backend python", limit=2)

        self.assertEqual([score for _, score in results], [0.0, 1.0])


if __name__ == "__main__":
    unittest.main()
