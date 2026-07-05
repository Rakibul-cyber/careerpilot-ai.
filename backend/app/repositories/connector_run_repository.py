# Data-access layer for the ConnectorRun aggregate.
#
# Audit records for connector executions. Reads exclude soft-deleted rows and
# are ordered newest-run-first. No business logic here.

# Deferred annotations: the `list` method shadows the builtin `list` in the
# class namespace, so keep return hints (`-> list[ConnectorRun]`) as strings.
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.connector_run import ConnectorRun


class ConnectorRunRepository:
    """Persistence operations for :class:`ConnectorRun`."""

    def create(self, db: Session, connector_run: ConnectorRun) -> ConnectorRun:
        """Persist a new connector run."""
        db.add(connector_run)
        db.commit()
        db.refresh(connector_run)
        return connector_run

    def update(self, db: Session, connector_run: ConnectorRun) -> ConnectorRun:
        """Flush pending changes on an already-tracked connector run."""
        db.commit()
        db.refresh(connector_run)
        return connector_run

    def get_by_id(self, db: Session, run_id: UUID) -> ConnectorRun | None:
        """Return the live connector run with this id, or None."""
        stmt = select(ConnectorRun).where(
            ConnectorRun.id == run_id,
            ConnectorRun.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list(
        self, db: Session, skip: int = 0, limit: int = 50
    ) -> list[ConnectorRun]:
        """Return a page of live connector runs, newest run first."""
        stmt = (
            select(ConnectorRun)
            .where(ConnectorRun.deleted_at.is_(None))
            .order_by(ConnectorRun.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())
