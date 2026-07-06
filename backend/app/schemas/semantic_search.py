# Pydantic v2 schemas for job embeddings + semantic search (M31).
#
# The embedding vector itself is never exposed — only its status/metadata.

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.job import JobEmbeddingStatus
from app.schemas.job import JobRead


class JobEmbeddingRead(BaseModel):
    """Embedding status/metadata for a job (no vector)."""

    job_id: UUID
    embedding_status: JobEmbeddingStatus
    embedding_model: str | None
    embedding_error: str | None
    embedded_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SemanticSearchRequest(BaseModel):
    """Request body for POST /jobs/semantic-search."""

    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=20, ge=1, le=100)


class SemanticSearchResult(BaseModel):
    """One ranked job with its similarity to the query."""

    job: JobRead
    similarity_score: float

    model_config = ConfigDict(from_attributes=True)


class EmbeddingRebuildResponse(BaseModel):
    """Outcome of a batch embedding rebuild."""

    processed: int
    succeeded: int
    failed: int
