# Authentication transport schemas.

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Token(BaseModel):
    """JWT access-token response returned by the login endpoint."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Decoded JWT claims. Validation coerces sub->UUID and exp->datetime."""

    sub: UUID
    type: str
    exp: datetime
