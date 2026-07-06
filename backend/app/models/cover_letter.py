# CoverLetter entity — an AI-generated, tailored cover letter (M30).
#
# Built from a parsed ResumeProfile + a Job (+ optional JobMatch). No PDF/DOCX
# export, no email, no applications table yet. Multiple letters per (profile,
# job) are allowed (different tone/language, or regeneration), so there is no
# uniqueness constraint. The AI is reached only via AICoverLetterClient.

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import BaseModel
from app.models.job import Job  # noqa: F401  (registers "Job" mapper)
from app.models.job_match import JobMatch  # noqa: F401
from app.models.resume_profile import ResumeProfile  # noqa: F401
from app.models.user import User  # noqa: F401  (registers "User" mapper)


class CoverLetterStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class CoverLetter(BaseModel, Base):
    __tablename__ = "cover_letters"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resume_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Optional match used to steer the letter; nullable.
    job_match_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_matches.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Free-form for now (e.g. "en", "de"); default English / professional.
    language: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="en"
    )
    tone: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="professional"
    )

    # The generated letter; NULL until generation succeeds (or on failure).
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    generation_status: Mapped[CoverLetterStatus] = mapped_column(
        Enum(
            CoverLetterStatus,
            name="cover_letter_status",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        default=CoverLetterStatus.PENDING,
        server_default=CoverLetterStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    # Failure reason when generation_status == FAILED; NULL otherwise.
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Verbatim AI response, kept for debugging failed / surprising output.
    raw_ai_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # When generation last completed (success or failure).
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User")
    resume_profile = relationship("ResumeProfile")
    job = relationship("Job")
    job_match = relationship("JobMatch")
