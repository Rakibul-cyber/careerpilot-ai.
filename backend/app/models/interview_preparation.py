# InterviewPreparation entity (M34) -- structured AI-generated coaching package
# for an Application. Stores JSONB arrays with shape preserved for future UI.

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.application import Application  # noqa: F401
from app.models.base import BaseModel
from app.models.user import User  # noqa: F401


class InterviewPreparationStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class InterviewDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class InterviewPreparation(BaseModel, Base):
    __tablename__ = "interview_preparations"
    __table_args__ = (
        Index(
            "uq_interview_preparations_application_id",
            "application_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_interview_preparations_user_id", "user_id"),
        Index("ix_interview_preparations_application_id", "application_id"),
        Index(
            "ix_interview_preparations_generation_status",
            "generation_status",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
    )

    generation_status: Mapped[InterviewPreparationStatus] = mapped_column(
        Enum(
            InterviewPreparationStatus,
            name="interview_preparation_status",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        default=InterviewPreparationStatus.PENDING,
        server_default=InterviewPreparationStatus.PENDING.value,
        nullable=False,
    )
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    weaknesses: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    technical_questions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    behavioral_questions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    company_questions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    study_topics: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    interview_tips: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    estimated_difficulty: Mapped[InterviewDifficulty | None] = mapped_column(
        Enum(
            InterviewDifficulty,
            name="interview_difficulty",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=True,
    )

    raw_ai_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User")
    application = relationship("Application")
