# Application entity (M33) -- the source of truth for a user's interaction with
# a job. It links to existing artifacts instead of copying their content.

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import BaseModel
from app.models.cover_letter import CoverLetter  # noqa: F401
from app.models.job import Job  # noqa: F401
from app.models.job_recommendation import JobRecommendation  # noqa: F401
from app.models.resume_profile import ResumeProfile  # noqa: F401
from app.models.user import User  # noqa: F401


class ApplicationStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"
    APPLIED = "applied"
    VIEWED = "viewed"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL_INTERVIEW = "technical_interview"
    HR_INTERVIEW = "hr_interview"
    FINAL_INTERVIEW = "final_interview"
    OFFER = "offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ApplicationSource(str, enum.Enum):
    MANUAL = "manual"
    RECOMMENDATION = "recommendation"
    JOB_ALERT = "job_alert"
    EXTERNAL_IMPORT = "external_import"


class Application(BaseModel, Base):
    __tablename__ = "applications"
    __table_args__ = (
        Index("ix_applications_user_id", "user_id"),
        Index("ix_applications_job_id", "job_id"),
        Index("ix_applications_resume_profile_id", "resume_profile_id"),
        Index("ix_applications_status", "status"),
        Index("ix_applications_source", "source"),
        Index("ix_applications_created_at", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resume_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    cover_letter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cover_letters.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_recommendation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_recommendations.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(
            ApplicationStatus,
            name="application_status",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        default=ApplicationStatus.DRAFT,
        server_default=ApplicationStatus.DRAFT.value,
        nullable=False,
    )
    source: Mapped[ApplicationSource] = mapped_column(
        Enum(
            ApplicationSource,
            name="application_source",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        default=ApplicationSource.MANUAL,
        server_default=ApplicationSource.MANUAL.value,
        nullable=False,
    )

    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_status_change_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    interview_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    offer_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    follow_up_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User")
    job = relationship("Job")
    resume_profile = relationship("ResumeProfile")
    cover_letter = relationship("CoverLetter")
    job_recommendation = relationship("JobRecommendation")
