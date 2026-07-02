# Shared FastAPI dependency providers for the API layer.
#
# get_db already lives in app.db.session; it is re-exported here so endpoints
# have a single import point for dependencies. Service providers and the
# current-user resolver are wired here, keeping construction and auth plumbing
# out of the route handlers.

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db  # noqa: F401  (re-exported dependency)
from app.models.user import User
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_user_service() -> UserService:
    return UserService()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Resolve the authenticated user from a bearer token.

    Returns an identical 401 for every failure mode (bad/expired token, missing
    or non-UUID subject, unknown or inactive user) so nothing about why auth
    failed is leaked.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
        user_id = UUID(subject)
    except (JWTError, ValueError):
        raise credentials_exception

    user = user_service.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user
