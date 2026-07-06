# Data-access layer for job embeddings + vector similarity search (M31).
#
# Kept separate from JobRepository so the vector-specific SQL lives in one
# place. Semantic search excludes soft-deleted and non-ACTIVE jobs and jobs
# without an embedding, and orders by cosine distance (deterministic for a
# given query vector and stored vectors).

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import Job, JobEmbeddingStatus, JobStatus


class JobEmbeddingRepository:
    """Vector persistence + similarity queries for :class:`Job`."""

    def semantic_search(
        self, db: Session, query_vector: list[float], limit: int
    ) -> list[tuple[Job, float]]:
        """Return (job, cosine_distance) for the nearest ACTIVE, live jobs.

        Smaller distance = more similar. Callers convert to a similarity score.
        """
        distance = Job.embedding.cosine_distance(query_vector)
        stmt = (
            select(Job, distance.label("distance"))
            .where(
                Job.deleted_at.is_(None),
                Job.status == JobStatus.ACTIVE,
                Job.embedding.is_not(None),
            )
            .order_by(distance.asc())
            .limit(limit)
        )
        return [(row[0], float(row[1])) for row in db.execute(stmt).all()]

    def list_active_needing_embedding(
        self, db: Session, limit: int
    ) -> list[Job]:
        """Return live ACTIVE jobs whose embedding is pending or failed."""
        stmt = (
            select(Job)
            .where(
                Job.deleted_at.is_(None),
                Job.status == JobStatus.ACTIVE,
                Job.embedding_status.in_(
                    [JobEmbeddingStatus.PENDING, JobEmbeddingStatus.FAILED]
                ),
            )
            .order_by(Job.created_at.asc())
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def get_active_by_id(
        self, db: Session, job_id: UUID
    ) -> Job | None:
        """Return the live ACTIVE job with this id, or None."""
        stmt = select(Job).where(
            Job.id == job_id,
            Job.deleted_at.is_(None),
            Job.status == JobStatus.ACTIVE,
        )
        return db.execute(stmt).scalar_one_or_none()
