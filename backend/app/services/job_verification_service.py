# Job lifecycle / verification service.
#
# Manages Job status transitions only (active <-> expired -> archived) and the
# last_verified_at stamp. No external HTTP checking here: future scrapers or
# checkers decide liveness and call mark_verified / mark_expired. This service
# also surfaces the candidate queries (stale / expired / archivable) used by a
# future scheduler.

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.job import Job, JobStatus
from app.repositories.job_repository import JobRepository

logger = get_logger(__name__)


class JobVerificationService:
    def __init__(self, job_repository: JobRepository | None = None) -> None:
        self.job_repository = job_repository or JobRepository()

    def mark_verified(self, db: Session, job: Job) -> Job:
        """Stamp the job as verified now and (re)assert ACTIVE."""
        job.last_verified_at = datetime.now(UTC)
        job.status = JobStatus.ACTIVE
        return self.job_repository.update(db, job)

    def mark_expired(self, db: Session, job: Job) -> Job:
        """Transition the job to EXPIRED."""
        job.status = JobStatus.EXPIRED
        return self.job_repository.update(db, job)

    def mark_archived(self, db: Session, job: Job) -> Job:
        """Transition the job to ARCHIVED."""
        job.status = JobStatus.ARCHIVED
        return self.job_repository.update(db, job)

    def get_stale_active_jobs(
        self,
        db: Session,
        max_age_hours: int = 24,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Job]:
        """Active jobs not verified within the last ``max_age_hours`` hours."""
        older_than = datetime.now(UTC) - timedelta(hours=max_age_hours)
        return self.job_repository.list_stale_active_jobs(
            db, older_than=older_than, skip=skip, limit=limit
        )

    def expire_jobs_past_deadline(
        self,
        db: Session,
        limit: int = 100,
    ) -> list[Job]:
        """Mark every active job past its expires_at deadline as EXPIRED."""
        now = datetime.now(UTC)
        candidates = self.job_repository.list_expired_jobs(db, now=now, limit=limit)
        expired = [self.mark_expired(db, job) for job in candidates]
        logger.info("Expired jobs past deadline count=%d", len(expired))
        return expired

    def archive_old_expired_jobs(
        self,
        db: Session,
        retention_days: int = 30,
        limit: int = 100,
    ) -> list[Job]:
        """Archive expired jobs untouched for longer than ``retention_days``."""
        older_than = datetime.now(UTC) - timedelta(days=retention_days)
        candidates = self.job_repository.list_jobs_for_archival(
            db, older_than=older_than, limit=limit
        )
        archived = [self.mark_archived(db, job) for job in candidates]
        logger.info("Archived old expired jobs count=%d", len(archived))
        return archived
