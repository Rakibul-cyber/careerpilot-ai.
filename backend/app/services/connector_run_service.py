# Business-logic layer for the ConnectorRun aggregate.
#
# Manages the lifecycle of a connector-run audit record: start (RUNNING) then
# terminal mark_success / mark_failed with counts, timing, and error text.

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.connector_run import ConnectorRun, ConnectorRunStatus
from app.repositories.connector_run_repository import ConnectorRunRepository

logger = get_logger(__name__)


class ConnectorRunService:
    def __init__(
        self, connector_run_repository: ConnectorRunRepository | None = None
    ) -> None:
        self.connector_run_repository = (
            connector_run_repository or ConnectorRunRepository()
        )

    def start_run(self, db: Session, connector_name: str) -> ConnectorRun:
        """Open a new run in RUNNING state, stamped with started_at (UTC)."""
        run = ConnectorRun(
            connector_name=connector_name,
            status=ConnectorRunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        created = self.connector_run_repository.create(db, run)
        logger.info(
            "Connector run started run_id=%s connector=%s",
            created.id,
            connector_name,
        )
        return created

    def mark_success(
        self,
        db: Session,
        run: ConnectorRun,
        fetched_count: int,
        ingested_count: int,
    ) -> ConnectorRun:
        """Close a run as SUCCESS with final counts and finished_at."""
        run.status = ConnectorRunStatus.SUCCESS
        run.fetched_count = fetched_count
        run.ingested_count = ingested_count
        run.finished_at = datetime.now(UTC)
        updated = self.connector_run_repository.update(db, run)
        logger.info(
            "ConnectorRun SUCCESS run_id=%s connector=%s fetched=%d ingested=%d",
            updated.id,
            updated.connector_name,
            fetched_count,
            ingested_count,
        )
        return updated

    def mark_failed(
        self,
        db: Session,
        run: ConnectorRun,
        error_message: str,
        fetched_count: int = 0,
        ingested_count: int = 0,
    ) -> ConnectorRun:
        """Close a run as FAILED with an error message and partial counts."""
        run.status = ConnectorRunStatus.FAILED
        run.fetched_count = fetched_count
        run.ingested_count = ingested_count
        run.error_message = error_message
        run.finished_at = datetime.now(UTC)
        updated = self.connector_run_repository.update(db, run)
        logger.error(
            "ConnectorRun FAILED run_id=%s connector=%s fetched=%d "
            "ingested=%d error=%s",
            updated.id,
            updated.connector_name,
            fetched_count,
            ingested_count,
            error_message,
        )
        return updated

    def get_run(self, db: Session, run_id: UUID) -> ConnectorRun | None:
        return self.connector_run_repository.get_by_id(db, run_id)

    def list_runs(
        self, db: Session, skip: int = 0, limit: int = 50
    ) -> list[ConnectorRun]:
        return self.connector_run_repository.list(db, skip=skip, limit=limit)
