# Reusable columns shared by every ORM model (SQLAlchemy 2.x mixin).

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class BaseModel:
    """Mixin providing surrogate PK, audit timestamps, and soft-delete.

    Applied alongside ``Base`` on concrete models, e.g. ``class User(BaseModel, Base)``.
    Not itself a mapped class, so it defines no ``__tablename__``.
    """

    # Non-enumerable surrogate primary key generated application-side.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )

    # Row creation time, set by the database in UTC.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Last modification time; refreshed on every UPDATE.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Soft-delete marker; NULL means the row is live.
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
