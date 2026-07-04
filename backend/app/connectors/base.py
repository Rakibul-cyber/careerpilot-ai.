# Job-source connector interface.
#
# A connector's only job is to FETCH raw postings from one source and return
# them as RawJobInput DTOs. Connectors must NOT: touch the database, call
# repositories, deduplicate, or normalize beyond minimal source cleanup. All of
# that belongs to JobIngestionService (dedup/normalization) and the runner
# (orchestration).

from abc import ABC, abstractmethod

from app.schemas.ingestion import RawJobInput


class BaseJobSourceConnector(ABC):
    """Contract every job-source connector implements."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Stable identifier for this source (e.g. "mock", "linkedin")."""
        ...

    @abstractmethod
    def fetch_jobs(self) -> list[RawJobInput]:
        """Return raw job postings from the source as RawJobInput DTOs."""
        ...
