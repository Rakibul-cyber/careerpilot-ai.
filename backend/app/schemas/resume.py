# Pydantic v2 transport schemas for the Resume resource.
# Decoupled from the ORM model; deleted_at and the local file_path are never
# exposed.

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.resume import ResumeExtractionStatus, ResumeFileType


class ResumeRead(BaseModel):
    """Public metadata for an uploaded resume (no file_path, no deleted_at)."""

    id: UUID
    user_id: UUID
    original_filename: str
    file_type: ResumeFileType
    mime_type: str
    file_size_bytes: int
    status: ResumeExtractionStatus
    extraction_error: str | None
    is_primary: bool
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeTextRead(BaseModel):
    """Just the extracted text of a resume."""

    id: UUID
    extracted_text: str | None

    model_config = ConfigDict(from_attributes=True)
