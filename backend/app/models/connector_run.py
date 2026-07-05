# ConnectorRun entity — an audit record of a single connector execution.
#
# Written by the runner before/after each run so schedulers and monitoring can
# see what happened (counts, timing, failures). Defines its own native enum
# connector_run_status.

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import BaseModel


class ConnectorRunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ConnectorRun(BaseModel, Base):
    __tablename__ = "connector_runs"

    connector_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    status: Mapped[ConnectorRunStatus] = mapped_column(
        Enum(
            ConnectorRunStatus,
            name="connector_run_status",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        default=ConnectorRunStatus.RUNNING,
        server_default=ConnectorRunStatus.RUNNING.value,
        nullable=False,
        index=True,
    )

    fetched_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    ingested_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
