# Data-access layer for the JobAlert aggregate.
#
# User-facing reads are scoped by user_id and exclude soft-deleted rows.
# list_due_alerts is a system query (not user-scoped) used by the runner to find
# alerts whose next_run_at has arrived. No business logic here.

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_alert import JobAlert


class JobAlertRepository:
    """Persistence operations for :class:`JobAlert`."""

    def get_by_id(self, db: Session, alert_id: UUID, user_id: UUID) -> JobAlert | None:
        """Return the user's live alert with this id, or None."""
        stmt = select(JobAlert).where(
            JobAlert.id == alert_id,
            JobAlert.user_id == user_id,
            JobAlert.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_saved_search(
        self, db: Session, user_id: UUID, saved_search_id: UUID
    ) -> JobAlert | None:
        """Return the user's live alert for this saved search, or None."""
        stmt = select(JobAlert).where(
            JobAlert.user_id == user_id,
            JobAlert.saved_search_id == saved_search_id,
            JobAlert.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_by_user(
        self, db: Session, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[JobAlert]:
        """Return a page of the user's live alerts, newest first."""
        stmt = (
            select(JobAlert)
            .where(
                JobAlert.user_id == user_id,
                JobAlert.deleted_at.is_(None),
            )
            .order_by(JobAlert.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def list_due_alerts(
        self, db: Session, now: datetime, limit: int = 100
    ) -> list[JobAlert]:
        """Return active alerts whose next_run_at has arrived (soonest first)."""
        stmt = (
            select(JobAlert)
            .where(
                JobAlert.deleted_at.is_(None),
                JobAlert.is_active.is_(True),
                JobAlert.next_run_at.is_not(None),
                JobAlert.next_run_at <= now,
            )
            .order_by(JobAlert.next_run_at.asc())
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    def create(self, db: Session, alert: JobAlert) -> JobAlert:
        """Persist a new alert."""
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    def update(self, db: Session, alert: JobAlert) -> JobAlert:
        """Flush pending changes on an already-tracked alert."""
        db.commit()
        db.refresh(alert)
        return alert

    def soft_delete(self, db: Session, alert: JobAlert) -> JobAlert:
        """Mark the alert deleted by stamping deleted_at (UTC)."""
        alert.deleted_at = datetime.now(UTC)
        db.commit()
        db.refresh(alert)
        return alert
