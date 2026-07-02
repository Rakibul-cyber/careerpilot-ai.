# schemas package.
# Pydantic models describing the API transport contract (request/response DTOs).
# One module per resource (e.g. user.py, resume.py). These define validation and
# serialization boundaries and are intentionally decoupled from ORM models.

from app.schemas.user import UserBase, UserCreate, UserRead, UserUpdate

__all__ = ["UserBase", "UserCreate", "UserUpdate", "UserRead"]
