# Business-logic layer for generating job embeddings (M31).
#
# Builds a normalized text representation of a job (title, company, location,
# employment type, description, requirements), calls the AIEmbeddingClient
# abstraction (never a provider SDK directly), and persists the vector plus an
# explicit embedding lifecycle. Provider/validation failures are captured on
# the row (embedding_status=failed) rather than raised, so a bad provider call
# never crashes the caller. This milestone embeds only jobs — not resumes.

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.job import Job, JobEmbeddingStatus
from app.repositories.job_embedding_repository import JobEmbeddingRepository
from app.repositories.job_repository import JobRepository
from app.services.ai.base_embedding_client import AIEmbeddingClient
from app.services.ai.openai_embedding_client import OpenAIEmbeddingClient

logger = get_logger(__name__)


class JobNotFoundError(Exception):
    """Job missing or soft-deleted (-> HTTP 404)."""


class JobEmbeddingService:
    def __init__(
        self,
        job_repository: JobRepository | None = None,
        job_embedding_repository: JobEmbeddingRepository | None = None,
        embedding_client: AIEmbeddingClient | None = None,
    ) -> None:
        self.job_repository = job_repository or JobRepository()
        self.job_embedding_repository = (
            job_embedding_repository or JobEmbeddingRepository()
        )
        self.embedding_client = embedding_client or OpenAIEmbeddingClient()

    def embed_job(self, db: Session, job_id: uuid.UUID) -> Job:
        """Generate and persist the embedding for one job (upsert on the row)."""
        job = self.job_repository.get_by_id(db, job_id)
        if job is None:
            raise JobNotFoundError("Job not found")
        self._apply_embedding(job)
        return self.job_repository.update(db, job)

    def rebuild(self, db: Session, limit: int = 100) -> dict:
        """Embed active jobs whose embedding is pending or failed (batch).

        Commits per job so one provider failure doesn't roll back the others.
        """
        jobs = self.job_embedding_repository.list_active_needing_embedding(
            db, limit
        )
        succeeded = 0
        failed = 0
        for job in jobs:
            self._apply_embedding(job)
            self.job_repository.update(db, job)
            if job.embedding_status == JobEmbeddingStatus.COMPLETED:
                succeeded += 1
            else:
                failed += 1
        return {"processed": len(jobs), "succeeded": succeeded, "failed": failed}

    def _apply_embedding(self, job: Job) -> None:
        """Embed the job text, capturing failures on the row (never raising)."""
        try:
            vector = self.embedding_client.embed_text(self._job_text(job))
            job.embedding = vector
            job.embedding_model = self.embedding_client.model_name
            job.embedding_status = JobEmbeddingStatus.COMPLETED
            job.embedding_error = None
            job.embedded_at = datetime.now(timezone.utc)
            logger.info("Job embedded job_id=%s", job.id)
        except Exception as exc:
            # Keep any previously-good vector; record the failure explicitly.
            job.embedding_status = JobEmbeddingStatus.FAILED
            job.embedding_error = f"{type(exc).__name__}: {exc}"
            job.embedded_at = datetime.now(timezone.utc)
            logger.exception("Job embedding failed job_id=%s", job.id)

    @staticmethod
    def _job_text(job: Job) -> str:
        """Normalized text used as the embedding input."""
        company = job.company.name if job.company else ""
        parts = [
            f"Title: {job.title}",
            f"Company: {company}",
            f"Location: {job.location or ''}",
            f"Employment type: {job.employment_type or ''}",
            f"Description: {job.description or ''}",
            f"Requirements: {job.requirements or ''}",
        ]
        return "\n".join(parts)
