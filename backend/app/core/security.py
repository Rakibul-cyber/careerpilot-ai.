# Password hashing utilities.
#
# Centralizes hashing so no other layer touches passlib directly. Plaintext
# passwords are never logged, stored, or returned — only bcrypt hashes leave
# this module.

from passlib.context import CryptContext

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
