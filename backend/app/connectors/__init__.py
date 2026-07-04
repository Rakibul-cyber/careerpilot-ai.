# connectors package.
# Job-source connector framework: connectors fetch raw postings (RawJobInput);
# the runner orchestrates fetch -> ingest; JobIngestionService owns dedup and
# normalization. No external I/O lives here yet (mock connector only).

from app.connectors.base import BaseJobSourceConnector
from app.connectors.connector_runner import ConnectorRunner, ConnectorRunResult
from app.connectors.mock_job_connector import MockJobConnector

__all__ = [
    "BaseJobSourceConnector",
    "MockJobConnector",
    "ConnectorRunner",
    "ConnectorRunResult",
]
