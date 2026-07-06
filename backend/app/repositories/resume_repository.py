# Data-access layer for the Resume aggregate.
#
# All reads are scoped by user_id and exclude soft-deleted rows. No business
# logic here (file handling / extraction / primary rules live in the service).
# List results are newest-first.

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.resume import Resume


class ResumeRepository:
    """Persistence operations for :class:`Resume`."""

    def create(self, db: Session, resume: Resume) -> Resume:
        """Persist a new resume."""
        db.add(resume)
        db.commit()
        db.refresh(resume)
        return resume

    def get_by_id(
        self, db: Session, resume_id: UUID, user_id: UUID
    ) -> Resume | None:
        """Return the user's live resume with this id, or None."""
        stmt = select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user_id,
            Resume.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_by_user(
        self, db: Session, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[Resume]:
        """Return a page of the user's live resumes, newest first."""
        stmt = (
            select(Resume)
            .where(
                Resume.user_id == user_id,
                Resume.deleted_at.is_(None),
            )
            .order_by(Resume.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def update(self, db: Session, resume: Resume) -> Resume:
        """Flush pending changes on an already-tracked resume."""
        db.commit()
        db.refresh(resume)
        return resume

    def soft_delete(self, db: Session, resume: Resume) -> Resume:
        """Mark the resume deleted by stamping deleted_at (UTC)."""
        resume.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(resume)
        return resume

    def clear_primary_for_user(self, db: Session, user_id: UUID) -> None:
        """Unset is_primary on all of the user's live resumes."""
        stmt = (
            update(Resume)
            .where(
                Resume.user_id == user_id,
                Resume.deleted_at.is_(None),
                Resume.is_primary.is_(True),
            )
            .values(is_primary=False)
        )
        db.execute(stmt)
        db.commit()
