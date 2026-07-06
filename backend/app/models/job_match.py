# JobMatch entity — a deterministic match between a parsed resume profile and a
# job (M29). No AI, embeddings, or semantic similarity here (that arrives in
# M31); scores come from a rule-based scorer over ResumeProfile + Job text.
#
# One live match per (resume_profile, job). Scores are 0-100 (overall) with the
# component sub-scores summing into it; details live in JSONB columns.

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
from app.models.resume_profile import ResumeProfile  # noqa: F401
from app.models.user import User  # noqa: F401  (registers "User" mapper)


class JobMatch(BaseModel, Base):
    __tablename__ = "job_matches"
    __table_args__ = (
        # One live match per (resume_profile, job). Partial so a match can be
        # recreated after a soft delete, matching the codebase pattern.
        Index(
            "uq_job_matches_profile_job",
            "resume_profile_id",
            "job_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_job_matches_user_id", "user_id"),
        Index("ix_job_matches_resume_profile_id", "resume_profile_id"),
        Index("ix_job_matches_job_id", "job_id"),
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
    # Denormalized owner (== resume_profile.user_id) so matches can be listed
    # and authorized without joining through the profile.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Overall 0-100; components sum into it (skills 50 / title 20 /
    # experience 15 / location+language 15).
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    skill_score: Mapped[float] = mapped_column(Float, nullable=False)
    title_score: Mapped[float] = mapped_column(Float, nullable=False)
    location_score: Mapped[float] = mapped_column(Float, nullable=False)
    experience_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Details (JSONB): lists of strings / structured breakdown.
    matched_skills: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    missing_skills: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    match_reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    risk_flags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Full scorer breakdown (weights, ratios, token sets) for auditing that the
    # score is deterministic.
    raw_match_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # When the match was last (re)computed.
    matched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    resume_profile = relationship("ResumeProfile")
    job = relationship("Job")
    user = relationship("User")
