# Authentication HTTP endpoints (v1).
#
# Thin transport layer: takes the OAuth2 password form, delegates credential
# checking to UserService, and mints a JWT access token. No business logic here.

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_user_service
from app.core.security import create_access_token
from app.schemas.auth import Token
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> Token:
    """Exchange email (username) + password for a JWT access token."""
    user = user_service.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=str(user.id))
    return Token(access_token=token, token_type="bearer")
