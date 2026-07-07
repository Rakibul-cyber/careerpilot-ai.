# Connector orchestration + run tracking.
#
# The runner owns the fetch -> ingest loop and records an auditable ConnectorRun
# for every execution (RUNNING -> SUCCESS/FAILED). Connectors never touch the
# DB; JobIngestionService owns normalization/dedup; ConnectorRunService owns the
# audit record.

from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.connectors.base import BaseJobSourceConnector
from app.core.logging import get_logger
from app.models.connector_run import ConnectorRunStatus
from app.services.connector_run_service import ConnectorRunService
from app.services.job_ingestion_service import JobIngestionService

logger = get_logger(__name__)


class ConnectorRunResult(BaseModel):
    """Summary of a single connector run (mirrors the persisted ConnectorRun)."""

    run_id: UUID
    connector_name: str
    status: ConnectorRunStatus
    fetched_count: int
    ingested_count: int
    job_ids: list[UUID]
    error_message: str | None = None


class ConnectorRunner:
    def __init__(
        self,
        ingestion_service: JobIngestionService | None = None,
        connector_run_service: ConnectorRunService | None = None,
    ) -> None:
        self.ingestion_service = ingestion_service or JobIngestionService()
        self.connector_run_service = connector_run_service or ConnectorRunService()

    def run(self, db: Session, connector: BaseJobSourceConnector) -> ConnectorRunResult:
        """Fetch + ingest, recording a ConnectorRun audit row for the attempt.

        On failure the run is marked FAILED with the error and whatever partial
        counts were reached; the exception is swallowed (not re-raised).
        """
        logger.info("Running connector %s", connector.source_name)
        run = self.connector_run_service.start_run(db, connector.source_name)

        fetched_count = 0
        ingested_count = 0
        job_ids: list[UUID] = []

        try:
            raw_jobs = connector.fetch_jobs()
            fetched_count = len(raw_jobs)
            for raw_job in raw_jobs:
                job = self.ingestion_service.ingest_job(db, raw_job)
                job_ids.append(job.id)
                ingested_count += 1

            self.connector_run_service.mark_success(
                db, run, fetched_count=fetched_count, ingested_count=ingested_count
            )
            logger.info(
                "Connector completed connector=%s fetched=%d ingested=%d",
                connector.source_name,
                fetched_count,
                ingested_count,
            )
            return ConnectorRunResult(
                run_id=run.id,
                connector_name=connector.source_name,
                status=ConnectorRunStatus.SUCCESS,
                fetched_count=fetched_count,
                ingested_count=ingested_count,
                job_ids=job_ids,
                error_message=None,
            )
        except Exception as exc:  # noqa: BLE001 (record failure, don't re-raise)
            # A failed ingest may leave the session mid-transaction; clear it so
            # the FAILED audit row can be committed. Already-ingested jobs were
            # committed per-job, so they survive this rollback.
            db.rollback()
            error_message = f"{type(exc).__name__}: {exc}"
            logger.exception(
                "Connector failed connector=%s fetched=%d ingested=%d",
                connector.source_name,
                fetched_count,
                ingested_count,
            )
            self.connector_run_service.mark_failed(
                db,
                run,
                error_message=error_message,
                fetched_count=fetched_count,
                ingested_count=ingested_count,
            )
            return ConnectorRunResult(
                run_id=run.id,
                connector_name=connector.source_name,
                status=ConnectorRunStatus.FAILED,
                fetched_count=fetched_count,
                ingested_count=ingested_count,
                job_ids=job_ids,
                error_message=error_message,
            )
