# Scheduled job functions.
#
# Each job owns its DB session (opened here, closed in finally), sets a fresh
# execution_id for log correlation, and logs start/success/failure. Exceptions
# are logged and re-raised so APScheduler records the job as failed — nothing is
# swallowed silently.

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.connectors.connector_runner import ConnectorRunner
from app.connectors.mock_job_connector import MockJobConnector
from app.core.logging import get_logger
from app.core.request_context import reset_execution_id, set_execution_id
from app.db.session import SessionLocal
from app.services.job_alert_service import JobAlertService
from app.services.job_verification_service import JobVerificationService

logger = get_logger(__name__)


@contextmanager
def _scheduled_job(job_name: str) -> Iterator[Session]:
    """Shared job scaffolding: execution_id + DB session + start/end logging."""
    execution_id = str(uuid.uuid4())
    token = set_execution_id(execution_id)
    db = SessionLocal()
    logger.info("Scheduled job started job=%s", job_name)
    try:
        yield db
    except Exception:
        logger.exception("Scheduled job failed job=%s", job_name)
        raise  # let APScheduler record the failure
    else:
        logger.info("Scheduled job completed job=%s", job_name)
    finally:
        db.close()
        reset_execution_id(token)


def run_mock_connector_job() -> None:
    """Run the mock connector through the ingestion pipeline."""
    with _scheduled_job("run_mock_connector_job") as db:
        result = ConnectorRunner().run(db, MockJobConnector())
        logger.info(
            "Mock connector job result run_id=%s status=%s fetched=%d ingested=%d",
            result.run_id,
            result.status.value,
            result.fetched_count,
            result.ingested_count,
        )


def expire_jobs_job() -> None:
    """Expire active jobs past their deadline."""
    with _scheduled_job("expire_jobs_job") as db:
        expired = JobVerificationService().expire_jobs_past_deadline(db)
        logger.info("Expire jobs job count=%d", len(expired))


def archive_jobs_job() -> None:
    """Archive expired jobs older than the retention window."""
    with _scheduled_job("archive_jobs_job") as db:
        archived = JobVerificationService().archive_old_expired_jobs(db)
        logger.info("Archive jobs job count=%d", len(archived))


def run_due_alerts_job() -> None:
    """Run every job alert whose next_run_at has arrived."""
    with _scheduled_job("run_due_alerts_job") as db:
        alerts = JobAlertService().run_due_alerts(db)
        logger.info("Run due alerts job count=%d", len(alerts))
