# Pydantic v2 transport schemas for the Application resource (M33).

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.application import ApplicationSource, ApplicationStatus


class ApplicationCreate(BaseModel):
    """Payload for POST /applications.

    Manual creation requires job_id + resume_profile_id. When
    job_recommendation_id is provided, the service can derive both.
    """

    job_id: UUID | None = None
    resume_profile_id: UUID | None = None
    cover_letter_id: UUID | None = None
    job_recommendation_id: UUID | None = None
    status: ApplicationStatus = ApplicationStatus.DRAFT
    source: ApplicationSource = ApplicationSource.MANUAL
    notes: str | None = Field(default=None, max_length=10000)
    company_response: str | None = Field(default=None, max_length=10000)
    interview_date: datetime | None = None
    follow_up_date: datetime | None = None


class ApplicationUpdate(BaseModel):
    """Partial update payload; status changes use /applications/{id}/status."""

    cover_letter_id: UUID | None = None
    job_recommendation_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=10000)
    company_response: str | None = Field(default=None, max_length=10000)
    interview_date: datetime | None = None
    follow_up_date: datetime | None = None


class ApplicationStatusUpdate(BaseModel):
    """Payload for PATCH /applications/{id}/status."""

    status: ApplicationStatus


class ApplicationRead(BaseModel):
    """Public representation of a job application."""

    id: UUID
    user_id: UUID
    job_id: UUID
    resume_profile_id: UUID
    cover_letter_id: UUID | None
    job_recommendation_id: UUID | None
    status: ApplicationStatus
    source: ApplicationSource
    applied_at: datetime | None
    last_status_change_at: datetime | None
    notes: str | None
    company_response: str | None
    interview_date: datetime | None
    offer_date: datetime | None
    rejection_date: datetime | None
    follow_up_date: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationFilter(BaseModel):
    """Internal filter DTO for application listing."""

    status: ApplicationStatus | None = None
    company: str | None = None
    source: ApplicationSource | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
