# Data-access layer for the ResumeProfile aggregate.
#
# All reads are scoped by user_id and exclude soft-deleted rows. No business
# logic here (parsing / validation lives in ResumeParserService).

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.resume_profile import ResumeProfile


class ResumeProfileRepository:
    """Persistence operations for :class:`ResumeProfile`."""

    def create(self, db: Session, profile: ResumeProfile) -> ResumeProfile:
        """Persist a new profile."""
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    def update(self, db: Session, profile: ResumeProfile) -> ResumeProfile:
        """Flush pending changes on an already-tracked profile."""
        db.commit()
        db.refresh(profile)
        return profile

    def get_by_resume(
        self, db: Session, resume_id: UUID, user_id: UUID
    ) -> ResumeProfile | None:
        """Return the user's live profile for this resume, or None."""
        stmt = select(ResumeProfile).where(
            ResumeProfile.resume_id == resume_id,
            ResumeProfile.user_id == user_id,
            ResumeProfile.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_id(
        self, db: Session, profile_id: UUID, user_id: UUID
    ) -> ResumeProfile | None:
        """Return the user's live profile with this id, or None."""
        stmt = select(ResumeProfile).where(
            ResumeProfile.id == profile_id,
            ResumeProfile.user_id == user_id,
            ResumeProfile.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_by_user(
        self, db: Session, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[ResumeProfile]:
        """Return a page of the user's live profiles, newest first."""
        stmt = (
            select(ResumeProfile)
            .where(
                ResumeProfile.user_id == user_id,
                ResumeProfile.deleted_at.is_(None),
            )
            .order_by(ResumeProfile.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def soft_delete(
        self, db: Session, profile: ResumeProfile
    ) -> ResumeProfile:
        """Mark the profile deleted by stamping deleted_at (UTC)."""
        profile.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(profile)
        return profile
