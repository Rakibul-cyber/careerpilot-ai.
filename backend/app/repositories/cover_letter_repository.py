# Data-access layer for the CoverLetter aggregate.
#
# All reads are scoped by user_id and exclude soft-deleted rows. No generation
# logic here (that lives in CoverLetterService). Lists are newest-first.

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cover_letter import CoverLetter


class CoverLetterRepository:
    """Persistence operations for :class:`CoverLetter`."""

    def create(self, db: Session, cover_letter: CoverLetter) -> CoverLetter:
        """Persist a new cover letter."""
        db.add(cover_letter)
        db.commit()
        db.refresh(cover_letter)
        return cover_letter

    def get_by_id(
        self, db: Session, cover_letter_id: UUID, user_id: UUID
    ) -> CoverLetter | None:
        """Return the user's live cover letter with this id, or None."""
        stmt = select(CoverLetter).where(
            CoverLetter.id == cover_letter_id,
            CoverLetter.user_id == user_id,
            CoverLetter.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_by_user(
        self, db: Session, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[CoverLetter]:
        """Return a page of the user's live cover letters, newest first."""
        stmt = (
            select(CoverLetter)
            .where(
                CoverLetter.user_id == user_id,
                CoverLetter.deleted_at.is_(None),
            )
            .order_by(CoverLetter.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def soft_delete(
        self, db: Session, cover_letter: CoverLetter
    ) -> CoverLetter:
        """Mark the cover letter deleted by stamping deleted_at (UTC)."""
        cover_letter.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(cover_letter)
        return cover_letter
