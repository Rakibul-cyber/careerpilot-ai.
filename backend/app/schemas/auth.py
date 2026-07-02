# Authentication transport schemas.

from pydantic import BaseModel


class Token(BaseModel):
    """JWT access-token response returned by the login endpoint."""

    access_token: str
    token_type: str = "bearer"
