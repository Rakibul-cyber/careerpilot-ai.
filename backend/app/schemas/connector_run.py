# Pydantic v2 transport schema for the ConnectorRun resource.
# Decoupled from the ORM model; deleted_at is never exposed.

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.connector_run import ConnectorRunStatus


class ConnectorRunRead(BaseModel):
    """Public representation of a connector run (audit record)."""

    id: UUID
    connector_name: str
    status: ConnectorRunStatus
    fetched_count: int
    ingested_count: int
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
