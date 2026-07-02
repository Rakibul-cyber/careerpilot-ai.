# Pydantic v2 transport schemas for the User resource.
# These define the API request/response contract and are decoupled from the ORM
# model. The password hash is never exposed and never accepted as a hash here.

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    """Fields shared by user create/read representations."""

    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """Payload for registering a new user (plaintext password in, never stored raw)."""

    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    """Partial update payload; every field is optional."""

    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=8)


class UserRead(BaseModel):
    """Public representation of a user. Excludes hashed_password and deleted_at."""

    id: UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_active: bool
    email_verified_at: datetime | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
