# User identity/authentication entity.

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    """Coarse-grained authorization role for a user account."""

    USER = "user"
    ADMIN = "admin"


class User(BaseModel, Base):
    __tablename__ = "users"

    # Primary login identifier and contact address.
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        index=True,
        nullable=False,
    )

    # Password hash; nullable so OAuth/SSO users need not have one.
    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Timestamp of email verification; NULL means unverified.
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Convenience display name; kept as a single culturally-neutral field.
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Authorization role.
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
        nullable=False,
        index=True,
    )

    # Account on/off switch, independent of soft delete.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # Last successful login; NULL until the first login.
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
