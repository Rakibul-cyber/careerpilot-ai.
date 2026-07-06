# JobRecommendation entity — a ranked job suggestion for a resume profile (M32).
#
# Orchestrates M31 (semantic search) + M29 (deterministic JobMatch scoring); no
# LLM ranking. final_score blends the two:
#     final_score = semantic_score * 40 + match_score * 0.60
# with semantic_score in [0,1], match_score in [0,100], final_score in [0,100].
#
# One live recommendation per (resume_profile, job) — re-running updates rather
# than duplicating.

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import BaseModel
from app.models.job import Job  # noqa: F401  (registers "Job" mapper)
from app.models.job_match import JobMatch  # noqa: F401
from app.models.resume_profile import ResumeProfile  # noqa: F401
from app.models.user import User  # noqa: F401  (registers "User" mapper)


class JobRecommendation(BaseModel, Base):
    __tablename__ = "job_recommendations"
    __table_args__ = (
        # One live recommendation per (resume_profile, job). Partial so it can
        # be recreated after a soft delete, matching the codebase pattern.
        Index(
            "uq_job_recommendations_profile_job",
            "resume_profile_id",
            "job_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_job_recommendations_user_id", "user_id"),
        Index(
            "ix_job_recommendations_resume_profile_id", "resume_profile_id"
        ),
        Index("ix_job_recommendations_job_id", "job_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resume_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    # The underlying deterministic match; SET NULL if that match is removed.
    job_match_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_matches.id", ondelete="SET NULL"),
        nullable=True,
    )

    semantic_score: Mapped[float] = mapped_column(Float, nullable=False)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)

    recommendation_reasons: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )
    risk_flags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Full blend breakdown (weights, component scores, match id) for auditing.
    raw_recommendation_data: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )

    recommended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User")
    resume_profile = relationship("ResumeProfile")
    job = relationship("Job")
    job_match = relationship("JobMatch")
