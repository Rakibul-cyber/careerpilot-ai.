# Business-logic layer for the JobAlert aggregate.
#
# Owns alert ownership rules, one-alert-per-saved-search, and the run logic that
# turns a saved search into a JobFilter, searches for matches, and reschedules
# the alert. No real email/scheduler yet — run_alert / run_due_alerts are the
# matching foundation a scheduler will call later.

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.job_alert import JobAlert, JobAlertFrequency
from app.repositories.job_alert_repository import JobAlertRepository
from app.schemas.job import JobFilter
from app.schemas.job_alert import JobAlertCreate, JobAlertUpdate
from app.services.job_service import JobService
from app.services.saved_search_service import SavedSearchService

# How far ahead to schedule the next run, per frequency.
_FREQUENCY_INTERVALS = {
    JobAlertFrequency.INSTANT: timedelta(hours=1),
    JobAlertFrequency.DAILY: timedelta(days=1),
    JobAlertFrequency.WEEKLY: timedelta(days=7),
}

# Upper bound on matches inspected per run (also caps last_match_count).
_RUN_MATCH_LIMIT = 100


class JobAlertService:
    def __init__(
        self,
        job_alert_repository: JobAlertRepository | None = None,
        saved_search_service: SavedSearchService | None = None,
        job_service: JobService | None = None,
    ) -> None:
        self.job_alert_repository = job_alert_repository or JobAlertRepository()
        self.saved_search_service = saved_search_service or SavedSearchService()
        self.job_service = job_service or JobService()

    def create_job_alert(
        self, db: Session, user_id: UUID, data: JobAlertCreate
    ) -> JobAlert:
        # Saved search must exist and belong to the user.
        saved_search = self.saved_search_service.get_saved_search(
            db, user_id, data.saved_search_id
        )
        if saved_search is None:
            raise LookupError("Saved search not found")

        # One alert per saved search per user.
        existing = self.job_alert_repository.get_by_saved_search(
            db, user_id, data.saved_search_id
        )
        if existing is not None:
            raise ValueError(
                "Job alert for this saved search already exists"
            )

        alert = JobAlert(user_id=user_id, **data.model_dump())
        return self.job_alert_repository.create(db, alert)

    def get_job_alert(
        self, db: Session, user_id: UUID, alert_id: UUID
    ) -> JobAlert | None:
        return self.job_alert_repository.get_by_id(db, alert_id, user_id)

    def list_job_alerts(
        self, db: Session, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[JobAlert]:
        return self.job_alert_repository.list_by_user(
            db, user_id, skip=skip, limit=limit
        )

    def update_job_alert(
        self,
        db: Session,
        user_id: UUID,
        alert_id: UUID,
        data: JobAlertUpdate,
    ) -> JobAlert | None:
        alert = self.job_alert_repository.get_by_id(db, alert_id, user_id)
        if alert is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(alert, field, value)

        return self.job_alert_repository.update(db, alert)

    def delete_job_alert(
        self, db: Session, user_id: UUID, alert_id: UUID
    ) -> JobAlert | None:
        alert = self.job_alert_repository.get_by_id(db, alert_id, user_id)
        if alert is None:
            return None
        return self.job_alert_repository.soft_delete(db, alert)

    def run_alert(self, db: Session, alert: JobAlert) -> list[Job]:
        """Run one alert: search its saved filter, record results, reschedule."""
        saved_search = alert.saved_search
        filters = JobFilter(
            query=saved_search.query,
            location=saved_search.location,
            employment_type=saved_search.employment_type,
            remote_type=saved_search.remote_type,
            status=saved_search.status,
            source=saved_search.source,
        )
        matches = self.job_service.search_jobs(
            db, filters=filters, skip=0, limit=_RUN_MATCH_LIMIT
        )

        now = datetime.now(timezone.utc)
        alert.last_run_at = now
        alert.last_match_count = len(matches)
        alert.next_run_at = now + _FREQUENCY_INTERVALS[alert.frequency]
        self.job_alert_repository.update(db, alert)

        return matches

    def run_due_alerts(
        self, db: Session, limit: int = 100
    ) -> list[JobAlert]:
        """Run every alert whose next_run_at has arrived; return those alerts."""
        now = datetime.now(timezone.utc)
        due = self.job_alert_repository.list_due_alerts(db, now, limit=limit)
        for alert in due:
            self.run_alert(db, alert)
        return due
