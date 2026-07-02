# Pydantic v2 transport schemas for the Company resource.
# Decoupled from the ORM model; deleted_at is never exposed.

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CompanyBase(BaseModel):
    """Fields shared across company create/read representations."""

    name: str
    normalized_name: str
    website_url: str | None = None
    linkedin_url: str | None = None
    career_page_url: str | None = None
    location: str | None = None


class CompanyCreate(CompanyBase):
    """Payload for creating a company."""


class CompanyUpdate(BaseModel):
    """Partial update payload; every field is optional."""

    name: str | None = None
    normalized_name: str | None = None
    website_url: str | None = None
    linkedin_url: str | None = None
    career_page_url: str | None = None
    location: str | None = None


class CompanyRead(CompanyBase):
    """Public representation of a company."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
