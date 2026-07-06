# ResumeProfile entity — the structured, AI-parsed form of a resume.
#
# One profile per resume (unique resume_id). Holds the LLM-extracted contact
# details plus flexible JSONB sections (skills, work history, education, ...),
# the raw AI response for debugging, and an explicit parse lifecycle. The parse
# is driven by ResumeParserService; nothing here calls the AI directly.

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import BaseModel
from app.models.resume import Resume  # noqa: F401  (registers "Resume" mapper)
from app.models.user import User  # noqa: F401  (registers "User" mapper)


class ResumeParseStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ResumeProfile(BaseModel, Base):
    __tablename__ = "resume_profiles"
    __table_args__ = (
        # One live profile per resume. Partial (deleted_at IS NULL) so a profile
        # can be recreated after a soft delete, matching the codebase pattern.
        Index(
            "uq_resume_profiles_resume_id",
            "resume_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_resume_profiles_user_id", "user_id"),
        Index("ix_resume_profiles_parse_status", "parse_status"),
    )

    # Backing resume; cascade so deleting the resume removes its profile.
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Owning user; cascade so a user's profiles are removed with the user.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Scalar contact / summary fields (all nullable — the AI may omit any).
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Flexible sections stored as JSONB (lists of strings or objects).
    skills: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    work_experience: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    education: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    projects: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    certifications: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    languages: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Verbatim AI response, kept for debugging failed / surprising parses.
    raw_ai_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Explicit parse lifecycle (pending -> completed/failed).
    parse_status: Mapped[ResumeParseStatus] = mapped_column(
        Enum(
            ResumeParseStatus,
            name="resume_parse_status",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        default=ResumeParseStatus.PENDING,
        server_default=ResumeParseStatus.PENDING.value,
        nullable=False,
    )
    # Failure reason when parse_status == FAILED; NULL otherwise.
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # When parsing last completed (success or failure).
    parsed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    resume = relationship("Resume")
    user = relationship("User")
