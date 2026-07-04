# Pydantic v2 transport schemas for the SavedSearch resource.
# Decoupled from the ORM model; deleted_at is never exposed.

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.job import JobSource, JobStatus


class SavedSearchBase(BaseModel):
    """Fields shared across saved-search create/read representations."""

    name: str
    query: str | None = None
    location: str | None = None
    employment_type: str | None = None
    remote_type: str | None = None
    status: JobStatus | None = None
    source: JobSource | None = None
    is_active: bool = True


class SavedSearchCreate(SavedSearchBase):
    """Payload for creating a saved search."""


class SavedSearchUpdate(BaseModel):
    """Partial update payload; every field is optional."""

    name: str | None = None
    query: str | None = None
    location: str | None = None
    employment_type: str | None = None
    remote_type: str | None = None
    status: JobStatus | None = None
    source: JobSource | None = None
    is_active: bool | None = None


class SavedSearchRead(SavedSearchBase):
    """Public representation of a saved search."""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
