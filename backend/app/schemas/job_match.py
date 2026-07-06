# Pydantic v2 schemas for the JobMatch resource.
#
# JobMatchRead is the public view — raw_match_data (the full scorer breakdown)
# is kept for debugging/audit and is intentionally not exposed.

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobMatchRead(BaseModel):
    """Public view of a resume-to-job match result."""

    id: UUID
    resume_profile_id: UUID
    job_id: UUID
    user_id: UUID
    overall_score: float
    skill_score: float
    title_score: float
    location_score: float
    experience_score: float
    matched_skills: list | None
    missing_skills: list | None
    match_reasons: list | None
    risk_flags: list | None
    matched_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
