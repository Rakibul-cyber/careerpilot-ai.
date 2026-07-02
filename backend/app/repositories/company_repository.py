# Data-access layer for the Company aggregate.
#
# Works purely with ORM models, contains no business logic (normalization lives
# in the service layer), and excludes soft-deleted rows (deleted_at IS NULL).

# Deferred annotations: the `list` method shadows the builtin `list` in the
# class namespace, so keep return hints (`-> list[Company]`) as strings.
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company


class CompanyRepository:
    """Persistence operations for :class:`Company`."""

    def get_by_id(self, db: Session, company_id: UUID) -> Company | None:
        """Return the live company with this id, or None."""
        stmt = select(Company).where(
            Company.id == company_id,
            Company.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_normalized_name(
        self, db: Session, normalized_name: str
    ) -> Company | None:
        """Return the live company with this normalized name, or None."""
        stmt = select(Company).where(
            Company.normalized_name == normalized_name,
            Company.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list(
        self, db: Session, skip: int = 0, limit: int = 50
    ) -> list[Company]:
        """Return a page of live companies, newest first."""
        stmt = (
            select(Company)
            .where(Company.deleted_at.is_(None))
            .order_by(Company.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def create(self, db: Session, company: Company) -> Company:
        """Persist a new company."""
        db.add(company)
        db.commit()
        db.refresh(company)
        return company

    def update(self, db: Session, company: Company) -> Company:
        """Flush pending changes on an already-tracked company instance."""
        db.commit()
        db.refresh(company)
        return company

    def soft_delete(self, db: Session, company: Company) -> Company:
        """Mark the company deleted by stamping deleted_at (UTC)."""
        company.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(company)
        return company
