# JobAlert entity — enables a saved search to be run on a schedule.
#
# One alert per (user, saved_search). Reuses no existing enum; defines its own
# job_alert_frequency native enum. Scheduling fields (last_run_at / next_run_at)
# are managed by the alert-run logic; no real scheduler/email yet.

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import BaseModel
from app.models.saved_search import SavedSearch  # noqa: F401  (registers mapper)
from app.models.user import User  # noqa: F401  (registers mapper)


class JobAlertFrequency(str, enum.Enum):
    INSTANT = "instant"
    DAILY = "daily"
    WEEKLY = "weekly"


class JobAlert(BaseModel, Base):
    __tablename__ = "job_alerts"
    __table_args__ = (
        # Partial unique index: one alert per (user, saved_search) among *live*
        # rows only, so an alert can be recreated after being soft-deleted.
        Index(
            "uq_job_alerts_user_saved_search",
            "user_id",
            "saved_search_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    # Owning user; cascade so a user's alerts are removed with the user.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Backing saved search; cascade so deleting it removes its alert.
    saved_search_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("saved_searches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    frequency: Mapped[JobAlertFrequency] = mapped_column(
        Enum(
            JobAlertFrequency,
            name="job_alert_frequency",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        default=JobAlertFrequency.DAILY,
        server_default=JobAlertFrequency.DAILY.value,
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        index=True,
    )

    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    last_match_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    user = relationship("User")
    saved_search = relationship("SavedSearch")
