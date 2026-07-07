# Password hashing utilities.
#
# Centralizes hashing so no other layer touches passlib directly. Plaintext
# passwords are never logged, stored, or returned — only bcrypt hashes leave
# this module.

from datetime import UTC, datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the given plaintext password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Check a plaintext password against a stored hash.

    Returns False (never raises) when no hash is stored — e.g. OAuth-only
    accounts that have never set a password.
    """
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    """Create a signed JWT access token for the given subject (user id)."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT, returning its claims.

    Raises jose.JWTError (or a subclass, e.g. ExpiredSignatureError) for any
    invalid or expired token. Callers are responsible for handling that.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
