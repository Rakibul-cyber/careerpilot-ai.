# Pydantic v2 schemas for the JobRecommendation resource.
#
# raw_recommendation_data (the full blend breakdown) is kept for auditing and
# is intentionally not exposed.

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobRecommendationRead(BaseModel):
    """Public view of a ranked job recommendation."""

    id: UUID
    user_id: UUID
    resume_profile_id: UUID
    job_id: UUID
    job_match_id: UUID | None
    semantic_score: float
    match_score: float
    final_score: float
    recommendation_reasons: list | None
    risk_flags: list | None
    recommended_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
