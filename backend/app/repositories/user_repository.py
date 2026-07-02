# Data-access layer for the User aggregate.
#
# Works purely with ORM models (never Pydantic schemas), contains no business
# logic, and never hashes passwords.
# All reads exclude soft-deleted rows
# (deleted_at IS NULL).

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Persistence operations for :class:`User`."""

    def get_by_id(self, db: Session, user_id: UUID) -> User | None:
        """Return the live (non-deleted) user with this id, or None."""
        stmt = select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, db: Session, email: str) -> User | None:
        """Return the live (non-deleted) user with this email, or None."""
        stmt = select(User).where(
            User.email == email,
            User.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def create(self, db: Session, user: User) -> User:
        """Persist a new user. Caller supplies a fully-formed ORM instance."""
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update(self, db: Session, user: User) -> User:
        """Flush pending changes on an already-tracked user instance."""
        db.commit()
        db.refresh(user)
        return user

    def soft_delete(self, db: Session, user: User) -> User:
        """Mark the user deleted by stamping deleted_at (UTC)."""
        user.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        return user
