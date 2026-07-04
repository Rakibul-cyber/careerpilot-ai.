# Pydantic v2 transport schemas for the Job resource.
# Decoupled from the ORM model; id/timestamps/deleted_at are not part of the base.

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.job import JobSource, JobStatus


class JobBase(BaseModel):
    """Fields shared across job create/read representations."""

    title: str
    normalized_title: str
    company_id: UUID
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
    status: JobStatus = JobStatus.ACTIVE
    posted_at: datetime | None = None
    expires_at: datetime | None = None
    last_verified_at: datetime | None = None


class JobCreate(JobBase):
    """Payload for creating a job."""


class JobUpdate(BaseModel):
    """Partial update payload; every field is optional."""

    title: str | None = None
    normalized_title: str | None = None
    company_id: UUID | None = None
    location: str | None = None
    remote_type: str | None = None
    employment_type: str | None = None
    source: JobSource | None = None
    source_url: str | None = None
    external_id: str | None = None
    description: str | None = None
    requirements: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
    status: JobStatus | None = None
    posted_at: datetime | None = None
    expires_at: datetime | None = None
    last_verified_at: datetime | None = None


class JobRead(JobBase):
    """Public representation of a job."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobFilter(BaseModel):
    """Internal filter DTO for job search. Pagination is passed separately."""

    query: str | None = None
    location: str | None = None
    employment_type: str | None = None
    remote_type: str | None = None
    status: JobStatus | None = None
    source: JobSource | None = None
