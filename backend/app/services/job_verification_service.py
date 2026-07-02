# Job lifecycle / verification service.
#
# Manages Job status transitions only (active <-> expired -> archived) and the
# last_verified_at stamp. No external HTTP checking here: future scrapers or
# checkers decide liveness and call mark_verified / mark_expired. This service
# also surfaces the candidate queries (stale / expired / archivable) used by a
# future scheduler.

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.job import Job, JobStatus
from app.repositories.job_repository import JobRepository


class JobVerificationService:
    def __init__(self, job_repository: JobRepository | None = None) -> None:
        self.job_repository = job_repository or JobRepository()

    def mark_verified(self, db: Session, job: Job) -> Job:
        """Stamp the job as verified now and (re)assert ACTIVE."""
        job.last_verified_at = datetime.now(timezone.utc)
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
        older_than = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        return self.job_repository.list_stale_active_jobs(
            db, older_than=older_than, skip=skip, limit=limit
        )

    def expire_jobs_past_deadline(
        self,
        db: Session,
        limit: int = 100,
    ) -> list[Job]:
        """Mark every active job past its expires_at deadline as EXPIRED."""
        now = datetime.now(timezone.utc)
        candidates = self.job_repository.list_expired_jobs(
            db, now=now, limit=limit
        )
        return [self.mark_expired(db, job) for job in candidates]

    def archive_old_expired_jobs(
        self,
        db: Session,
        retention_days: int = 30,
        limit: int = 100,
    ) -> list[Job]:
        """Archive expired jobs untouched for longer than ``retention_days``."""
        older_than = datetime.now(timezone.utc) - timedelta(days=retention_days)
        candidates = self.job_repository.list_jobs_for_archival(
            db, older_than=older_than, limit=limit
        )
        return [self.mark_archived(db, job) for job in candidates]
