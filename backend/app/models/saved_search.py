# SavedSearch entity — a reusable, named job-search filter owned by a user.
#
# Reuses the existing job_status / job_source enum types (does NOT define new
# ones). Will later power job alerts. One name per user is enforced by a unique
# constraint.

import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import BaseModel
from app.models.job import JobSource, JobStatus
from app.models.user import User  # noqa: F401  (registers "User" mapper)


class SavedSearch(BaseModel, Base):
    __tablename__ = "saved_searches"
    __table_args__ = (
        # Partial unique index: a user's saved-search names must be unique among
        # *live* rows only, so a soft-deleted name can be reused.
        Index(
            "uq_saved_searches_user_name",
            "user_id",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    # Owning user; cascade so a user's saved searches are removed with the user.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Filter criteria (mirror of JobFilter).
    query: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    remote_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Reuse existing enum types; create_type=False so the migration does not
    # attempt to (re)create job_status / job_source.
    status: Mapped[JobStatus | None] = mapped_column(
        Enum(
            JobStatus,
            name="job_status",
            create_type=False,
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=True,
    )
    source: Mapped[JobSource | None] = mapped_column(
        Enum(
            JobSource,
            name="job_source",
            create_type=False,
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    user = relationship("User")
