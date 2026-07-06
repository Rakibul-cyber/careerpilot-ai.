# Business-logic layer for semantic job search (M31).
#
# Embeds the query text via the AIEmbeddingClient abstraction and ranks ACTIVE,
# live, embedded jobs by cosine similarity. This sits *beside* the existing
# filter/full-text search (JobService) — it does not replace it. Provider
# failures raise EmbeddingAIError, which the API maps to a clean 502 rather
# than crashing.

from sqlalchemy.orm import Session

from app.models.job import Job
from app.repositories.job_embedding_repository import JobEmbeddingRepository
from app.services.ai.base_embedding_client import AIEmbeddingClient
from app.services.ai.openai_embedding_client import OpenAIEmbeddingClient


class SemanticJobSearchService:
    def __init__(
        self,
        job_embedding_repository: JobEmbeddingRepository | None = None,
        embedding_client: AIEmbeddingClient | None = None,
    ) -> None:
        self.job_embedding_repository = (
            job_embedding_repository or JobEmbeddingRepository()
        )
        self.embedding_client = embedding_client or OpenAIEmbeddingClient()

    def search(
        self, db: Session, query: str, limit: int = 20
    ) -> list[tuple[Job, float]]:
        """Return (job, similarity_score) ranked most-similar first.

        similarity_score = 1 - cosine_distance, clamped to 0..1 so higher is
        closer. Results are deterministic for a given query vector and stored
        vectors.
        """
        query_vector = self.embedding_client.embed_text(query)
        rows = self.job_embedding_repository.semantic_search(
            db, query_vector, limit
        )
        return [
            (job, round(max(0.0, min(1.0, 1.0 - distance)), 6))
            for job, distance in rows
        ]
