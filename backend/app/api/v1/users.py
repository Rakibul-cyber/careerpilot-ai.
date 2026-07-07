# User HTTP endpoints (v1).
#
# Thin transport layer: validate input, delegate to UserService, translate
# domain errors into HTTP responses. No business logic lives here.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    get_user_service,
    require_role,
)
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_create: UserCreate,
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    """Register a new user account."""
    try:
        user = user_service.create_user(db, user_create)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        ) from None
    return user


@router.get("/me", response_model=UserRead)
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the currently authenticated user."""
    return current_user


# --- TEMPORARY / DEV ONLY ---------------------------------------------------
# Throwaway endpoint used solely to verify the require_role RBAC dependency.
# Remove once real admin features (with their own routes) are implemented.
@router.get("/admin-check")
def admin_check(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    return {"message": "Admin access granted"}
