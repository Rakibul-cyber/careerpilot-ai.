# schemas package.
# Pydantic models describing the API transport contract (request/response DTOs).
# One module per resource (e.g. user.py, resume.py). These define validation and
# serialization boundaries and are intentionally decoupled from ORM models.

from app.schemas.auth import Token, TokenPayload
from app.schemas.company import (
    CompanyBase,
    CompanyCreate,
    CompanyRead,
    CompanyUpdate,
)
from app.schemas.ingestion import RawJobInput
from app.schemas.job import JobBase, JobCreate, JobRead, JobUpdate
from app.schemas.user import UserBase, UserCreate, UserRead, UserUpdate

__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserRead",
    "Token",
    "TokenPayload",
    "CompanyBase",
    "CompanyCreate",
    "CompanyUpdate",
    "CompanyRead",
    "JobBase",
    "JobCreate",
    "JobUpdate",
    "JobRead",
    "RawJobInput",
]
