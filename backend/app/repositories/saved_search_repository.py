# Data-access layer for the SavedSearch aggregate.
#
# All reads are scoped by user_id and exclude soft-deleted rows
# (deleted_at IS NULL). No business logic here (uniqueness checks live in the
# service). List results are newest-first.

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.saved_search import SavedSearch


class SavedSearchRepository:
    """Persistence operations for :class:`SavedSearch`."""

    def get_by_id(
        self, db: Session, saved_search_id: UUID, user_id: UUID
    ) -> SavedSearch | None:
        """Return the user's live saved search with this id, or None."""
        stmt = select(SavedSearch).where(
            SavedSearch.id == saved_search_id,
            SavedSearch.user_id == user_id,
            SavedSearch.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_name(self, db: Session, user_id: UUID, name: str) -> SavedSearch | None:
        """Return the user's live saved search with this name, or None."""
        stmt = select(SavedSearch).where(
            SavedSearch.user_id == user_id,
            SavedSearch.name == name,
            SavedSearch.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_by_user(
        self, db: Session, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[SavedSearch]:
        """Return a page of the user's live saved searches, newest first."""
        stmt = (
            select(SavedSearch)
            .where(
                SavedSearch.user_id == user_id,
                SavedSearch.deleted_at.is_(None),
            )
            .order_by(SavedSearch.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def create(self, db: Session, saved_search: SavedSearch) -> SavedSearch:
        """Persist a new saved search."""
        db.add(saved_search)
        db.commit()
        db.refresh(saved_search)
        return saved_search

    def update(self, db: Session, saved_search: SavedSearch) -> SavedSearch:
        """Flush pending changes on an already-tracked saved search."""
        db.commit()
        db.refresh(saved_search)
        return saved_search

    def soft_delete(self, db: Session, saved_search: SavedSearch) -> SavedSearch:
        """Mark the saved search deleted by stamping deleted_at (UTC)."""
        saved_search.deleted_at = datetime.now(UTC)
        db.commit()
        db.refresh(saved_search)
        return saved_search
