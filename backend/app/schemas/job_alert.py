# Pydantic v2 transport schemas for the JobAlert resource.
# Decoupled from the ORM model; deleted_at is never exposed.

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.job_alert import JobAlertFrequency


class JobAlertBase(BaseModel):
    """Fields a client supplies when creating an alert."""

    saved_search_id: UUID
    frequency: JobAlertFrequency = JobAlertFrequency.DAILY
    is_active: bool = True
    next_run_at: datetime | None = None


class JobAlertCreate(JobAlertBase):
    """Payload for creating a job alert."""


class JobAlertUpdate(BaseModel):
    """Partial update payload; every field is optional."""

    frequency: JobAlertFrequency | None = None
    is_active: bool | None = None
    next_run_at: datetime | None = None


class JobAlertRead(BaseModel):
    """Public representation of a job alert (includes run bookkeeping fields)."""

    id: UUID
    user_id: UUID
    saved_search_id: UUID
    frequency: JobAlertFrequency
    is_active: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    last_match_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
