# Pydantic v2 schemas for the CoverLetter resource.
#
#   * CoverLetterCreate      — the POST request body.
#   * CoverLetterAIOutput    — the *internal* contract the raw AI response must
#     validate against before the letter is saved (guards against empty/garbage
#     output).
#   * CoverLetterRead        — the public view (raw_ai_response is not exposed).

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.cover_letter import CoverLetterStatus


class CoverLetterCreate(BaseModel):
    """Request body for POST /cover-letters."""

    resume_profile_id: UUID
    job_id: UUID
    job_match_id: UUID | None = None
    language: str = Field(default="en", min_length=2, max_length=16)
    tone: str = Field(default="professional", min_length=2, max_length=32)


class CoverLetterAIOutput(BaseModel):
    """Structured shape the AI generator must return (validated before save)."""

    content: str

    model_config = ConfigDict(extra="ignore")

    @field_validator("content")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("cover letter content is empty")
        return v


class CoverLetterRead(BaseModel):
    """Public view of a generated cover letter (no raw_ai_response)."""

    id: UUID
    user_id: UUID
    resume_profile_id: UUID
    job_id: UUID
    job_match_id: UUID | None
    language: str
    tone: str
    content: str | None
    generation_status: CoverLetterStatus
    generation_error: str | None
    generated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
