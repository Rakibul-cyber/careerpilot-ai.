# Business-logic layer for the User aggregate.
#
# Orchestrates the repository and password hashing. This is where email
# normalization, uniqueness rules, and hashing live — the repository stays
# persistence-only and never sees a plaintext password.

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate

logger = get_logger(__name__)


class UserService:
    def __init__(self, user_repository: UserRepository | None = None) -> None:
        self.user_repository = user_repository or UserRepository()

    def get_user_by_id(self, db: Session, user_id: UUID) -> User | None:
        return self.user_repository.get_by_id(db, user_id)

    def get_user_by_email(self, db: Session, email: str) -> User | None:
        return self.user_repository.get_by_email(db, email.strip().lower())

    def create_user(self, db: Session, user_create: UserCreate) -> User:
        email = user_create.email.strip().lower()
        logger.info("Creating user email=%s", email)

        if self.user_repository.get_by_email(db, email) is not None:
            logger.info("User creation rejected, email exists email=%s", email)
            raise ValueError("User with this email already exists")

        user = User(
            email=email,
            full_name=user_create.full_name,
            hashed_password=hash_password(user_create.password),
        )
        created = self.user_repository.create(db, user)
        logger.info("User created user_id=%s email=%s", created.id, email)
        return created

    def update_user(self, db: Session, user: User, user_update: UserUpdate) -> User:
        if user_update.email is not None:
            email = user_update.email.strip().lower()
            if email != user.email:
                existing = self.user_repository.get_by_email(db, email)
                if existing is not None and existing.id != user.id:
                    raise ValueError("User with this email already exists")
                user.email = email

        if user_update.full_name is not None:
            user.full_name = user_update.full_name

        if user_update.password is not None:
            user.hashed_password = hash_password(user_update.password)

        return self.user_repository.update(db, user)

    def delete_user(self, db: Session, user: User) -> User:
        return self.user_repository.soft_delete(db, user)

    def authenticate_user(self, db: Session, email: str, password: str) -> User | None:
        """Return the user if credentials are valid and the account is usable.

        Returns None for unknown email, inactive account, passwordless
        (OAuth-only) account, or an incorrect password.
        """
        normalized_email = email.strip().lower()
        logger.info("Authenticating user email=%s", normalized_email)
        user = self.user_repository.get_by_email(db, normalized_email)
        if user is None:
            logger.info("Authentication failed, unknown email=%s", normalized_email)
            return None
        if not user.is_active:
            logger.info("Authentication failed, inactive user_id=%s", user.id)
            return None
        if not user.hashed_password:
            logger.info("Authentication failed, no password user_id=%s", user.id)
            return None
        if not verify_password(password, user.hashed_password):
            logger.info("Authentication failed, bad password user_id=%s", user.id)
            return None
        logger.info("User authenticated user_id=%s", user.id)
        return user
