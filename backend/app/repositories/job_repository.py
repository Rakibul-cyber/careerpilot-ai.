# Data-access layer for the Job aggregate.
#
# Works purely with ORM models, contains no business logic (normalization/dedup
# rules live in the service layer), and excludes soft-deleted rows
# (deleted_at IS NULL). List results are newest-first.

# Deferred annotations: the `list` method shadows the builtin `list` in the
# class namespace, which would break `-> list[Job]` return hints if evaluated
# eagerly. This keeps them as strings.
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.job import Job, JobSource, JobStatus


class JobRepository:
    """Persistence operations for :class:`Job`."""

    def get_by_id(self, db: Session, job_id: UUID) -> Job | None:
        """Return the live job with this id, or None."""
        stmt = select(Job).where(
            Job.id == job_id,
            Job.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_source_external_id(
        self, db: Session, source: JobSource, external_id: str
    ) -> Job | None:
        """Return the live job matching this (source, external_id) pair, or None."""
        stmt = select(Job).where(
            Job.source == source,
            Job.external_id == external_id,
            Job.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list(self, db: Session, skip: int = 0, limit: int = 50) -> list[Job]:
        """Return a page of live jobs, newest first."""
        stmt = (
            select(Job)
            .where(Job.deleted_at.is_(None))
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def list_by_company(
        self, db: Session, company_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[Job]:
        """Return a page of live jobs for one company, newest first."""
        stmt = (
            select(Job)
            .where(
                Job.company_id == company_id,
                Job.deleted_at.is_(None),
            )
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def list_stale_active_jobs(
        self,
        db: Session,
        older_than: datetime,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Job]:
        """Active jobs never verified or last verified before ``older_than``.

        Ordered oldest-verified first (NULLs first) so the most overdue jobs
        are processed before fresher ones.
        """
        stmt = (
            select(Job)
            .where(
                Job.deleted_at.is_(None),
                Job.status == JobStatus.ACTIVE,
                or_(
                    Job.last_verified_at.is_(None),
                    Job.last_verified_at < older_than,
                ),
            )
            .order_by(Job.last_verified_at.asc().nullsfirst())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def list_expired_jobs(
        self,
        db: Session,
        now: datetime,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Job]:
        """Active jobs whose expires_at deadline has passed."""
        stmt = (
            select(Job)
            .where(
                Job.deleted_at.is_(None),
                Job.status == JobStatus.ACTIVE,
                Job.expires_at.is_not(None),
                Job.expires_at < now,
            )
            .order_by(Job.expires_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def list_jobs_for_archival(
        self,
        db: Session,
        older_than: datetime,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Job]:
        """Expired jobs untouched since ``older_than`` (candidates to archive)."""
        stmt = (
            select(Job)
            .where(
                Job.deleted_at.is_(None),
                Job.status == JobStatus.EXPIRED,
                Job.updated_at < older_than,
            )
            .order_by(Job.updated_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def create(self, db: Session, job: Job) -> Job:
        """Persist a new job."""
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def update(self, db: Session, job: Job) -> Job:
        """Flush pending changes on an already-tracked job instance."""
        db.commit()
        db.refresh(job)
        return job

    def soft_delete(self, db: Session, job: Job) -> Job:
        """Mark the job deleted by stamping deleted_at (UTC)."""
        job.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        return job
