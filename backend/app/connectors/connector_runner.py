# Connector orchestration.
#
# The runner owns the fetch -> ingest loop. It pulls RawJobInput DTOs from a
# connector and hands each to JobIngestionService (which owns normalization and
# deduplication). Connectors never touch the DB; ingestion never fetches.

from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.connectors.base import BaseJobSourceConnector
from app.services.job_ingestion_service import JobIngestionService


class ConnectorRunResult(BaseModel):
    """Summary of a single connector run."""

    connector_name: str
    fetched_count: int
    ingested_count: int
    job_ids: list[UUID]


class ConnectorRunner:
    def __init__(
        self, ingestion_service: JobIngestionService | None = None
    ) -> None:
        self.ingestion_service = ingestion_service or JobIngestionService()

    def run(
        self, db: Session, connector: BaseJobSourceConnector
    ) -> ConnectorRunResult:
        """Fetch from the connector and ingest every posting it returns."""
        raw_jobs = connector.fetch_jobs()

        job_ids: list[UUID] = []
        for raw_job in raw_jobs:
            job = self.ingestion_service.ingest_job(db, raw_job)
            job_ids.append(job.id)

        return ConnectorRunResult(
            connector_name=connector.source_name,
            fetched_count=len(raw_jobs),
            ingested_count=len(job_ids),
            job_ids=job_ids,
        )
