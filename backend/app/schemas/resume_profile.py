# Pydantic v2 schemas for the ResumeProfile resource.
#
# Three concerns live here:
#   * ResumeProfile*AIOutput  — the *internal* contract the raw AI response must
#     validate against before anything is written to the DB. Lenient by design
#     (every field optional, extra keys ignored) so a sparse resume still parses.
#   * ResumeProfileRead       — the public read model (raw_ai_response is never
#     exposed; it exists only for debugging).
#   * ResumeProfileParseResponse — the POST /parse envelope carrying the outcome.

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.resume_profile import ResumeParseStatus


# --- Internal AI output contract -------------------------------------------
# Validated with model_validate_json() against the raw LLM text before the row
# is saved. Sub-sections are stored as JSONB, so their shape is captured here.


class ResumeWorkExperienceItem(BaseModel):
    company: str | None = None
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None

    model_config = ConfigDict(extra="ignore")


class ResumeEducationItem(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None

    model_config = ConfigDict(extra="ignore")


class ResumeProjectItem(BaseModel):
    name: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class ResumeProfileAIOutput(BaseModel):
    """Structured shape the AI parser must return (validated before save)."""

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    work_experience: list[ResumeWorkExperienceItem] = Field(default_factory=list)
    education: list[ResumeEducationItem] = Field(default_factory=list)
    projects: list[ResumeProjectItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


# --- Public transport schemas ----------------------------------------------


class ResumeProfileRead(BaseModel):
    """Public view of a parsed resume profile (no raw_ai_response)."""

    id: UUID
    resume_id: UUID
    user_id: UUID
    full_name: str | None
    email: str | None
    phone: str | None
    location: str | None
    summary: str | None
    skills: list | None
    work_experience: list | None
    education: list | None
    projects: list | None
    certifications: list | None
    languages: list | None
    parse_status: ResumeParseStatus
    parse_error: str | None
    parsed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeProfileParseResponse(BaseModel):
    """Outcome envelope for POST /resumes/{resume_id}/parse."""

    resume_id: UUID
    parse_status: ResumeParseStatus
    parse_error: str | None
    profile: ResumeProfileRead

    model_config = ConfigDict(from_attributes=True)
