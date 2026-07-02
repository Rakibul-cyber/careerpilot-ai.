# Internal ingestion DTO.
#
# RawJobInput is the contract future scrapers/importers hand to the ingestion
# service. It is NOT an API request body — it carries a raw company_name (not a
# company_id) because the service resolves/creates the Company during ingestion.

from datetime import datetime

from pydantic import BaseModel

from app.models.job import JobSource


class RawJobInput(BaseModel):
    """A raw, un-normalized job as received from a source before ingestion."""

    title: str
    company_name: str
    location: str | None = None
    remote_type: str | None = None
    employment_type: str | None = None
    source: JobSource = JobSource.OTHER
    source_url: str | None = None
    external_id: str | None = None
    description: str | None = None
    requirements: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
    posted_at: datetime | None = None
    expires_at: datetime | None = None
