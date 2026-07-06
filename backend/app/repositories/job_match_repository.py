# Data-access layer for the JobMatch aggregate.
#
# All reads are scoped by user_id and exclude soft-deleted rows. No scoring
# logic here (that lives in the scoring/match services). Lists are newest-first.

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_match import JobMatch


class JobMatchRepository:
    """Persistence operations for :class:`JobMatch`."""

    def create(self, db: Session, match: JobMatch) -> JobMatch:
        """Persist a new match."""
        db.add(match)
        db.commit()
        db.refresh(match)
        return match

    def update(self, db: Session, match: JobMatch) -> JobMatch:
        """Flush pending changes on an already-tracked match."""
        db.commit()
        db.refresh(match)
        return match

    def get_by_profile_job(
        self,
        db: Session,
        resume_profile_id: UUID,
        job_id: UUID,
        user_id: UUID,
    ) -> JobMatch | None:
        """Return the user's live match for this (profile, job), or None."""
        stmt = select(JobMatch).where(
            JobMatch.resume_profile_id == resume_profile_id,
            JobMatch.job_id == job_id,
            JobMatch.user_id == user_id,
            JobMatch.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_id(
        self, db: Session, match_id: UUID, user_id: UUID
    ) -> JobMatch | None:
        """Return the user's live match with this id, or None."""
        stmt = select(JobMatch).where(
            JobMatch.id == match_id,
            JobMatch.user_id == user_id,
            JobMatch.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_by_profile(
        self,
        db: Session,
        resume_profile_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[JobMatch]:
        """Return a page of the user's live matches for a profile."""
        stmt = (
            select(JobMatch)
            .where(
                JobMatch.resume_profile_id == resume_profile_id,
                JobMatch.user_id == user_id,
                JobMatch.deleted_at.is_(None),
            )
            .order_by(JobMatch.overall_score.desc(), JobMatch.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def soft_delete(self, db: Session, match: JobMatch) -> JobMatch:
        """Mark the match deleted by stamping deleted_at (UTC)."""
        match.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(match)
        return match
