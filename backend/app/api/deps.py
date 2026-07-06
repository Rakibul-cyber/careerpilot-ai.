# Shared FastAPI dependency providers for the API layer.
#
# get_db already lives in app.db.session; it is re-exported here so endpoints
# have a single import point for dependencies. Service providers and the
# current-user resolver are wired here, keeping construction and auth plumbing
# out of the route handlers.
from collections.abc import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db  # noqa: F401  (re-exported dependency)
from app.models.user import User, UserRole
from app.schemas.auth import TokenPayload
from app.services.company_service import CompanyService
from app.services.cover_letter_service import CoverLetterService
from app.services.job_alert_service import JobAlertService
from app.services.job_match_service import JobMatchService
from app.services.job_service import JobService
from app.services.resume_parser_service import ResumeParserService
from app.services.resume_service import ResumeService
from app.services.saved_search_service import SavedSearchService
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_user_service() -> UserService:
    return UserService()


def get_company_service() -> CompanyService:
    return CompanyService()


def get_job_service() -> JobService:
    return JobService()


def get_saved_search_service() -> SavedSearchService:
    return SavedSearchService()


def get_job_alert_service() -> JobAlertService:
    return JobAlertService()


def get_resume_service() -> ResumeService:
    return ResumeService()


def get_resume_parser_service() -> ResumeParserService:
    return ResumeParserService()


def get_job_match_service() -> JobMatchService:
    return JobMatchService()


def get_cover_letter_service() -> CoverLetterService:
    return CoverLetterService()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Resolve the authenticated user from a bearer access token.

    Returns an identical 401 for every failure mode (bad/expired token, missing
    or non-UUID subject, wrong token type, unknown or inactive user) so nothing
    about why auth failed is leaked.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = TokenPayload(**decode_access_token(token))
    except (JWTError, ValidationError):
        raise credentials_exception

    if payload.type != "access":
        raise credentials_exception

    user = user_service.get_user_by_id(db, payload.sub)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_role(required_role: UserRole) -> Callable[..., User]:
    """Build a dependency that allows only users holding ``required_role``.

    Authentication (401) is handled by get_current_user; this layer adds
    authorization, returning 403 when the identity is valid but lacks the role.
    """

    def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_user

    return role_checker
