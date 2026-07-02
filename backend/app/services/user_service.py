# Business-logic layer for the User aggregate.
#
# Orchestrates the repository and password hashing. This is where email
# normalization, uniqueness rules, and hashing live — the repository stays
# persistence-only and never sees a plaintext password.

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, user_repository: UserRepository | None = None) -> None:
        self.user_repository = user_repository or UserRepository()

    def get_user_by_id(self, db: Session, user_id: UUID) -> User | None:
        return self.user_repository.get_by_id(db, user_id)

    def get_user_by_email(self, db: Session, email: str) -> User | None:
        return self.user_repository.get_by_email(db, email.strip().lower())

    def create_user(self, db: Session, user_create: UserCreate) -> User:
        email = user_create.email.strip().lower()

        if self.user_repository.get_by_email(db, email) is not None:
            raise ValueError("User with this email already exists")

        user = User(
            email=email,
            full_name=user_create.full_name,
            hashed_password=hash_password(user_create.password),
        )
        return self.user_repository.create(db, user)

    def update_user(
        self, db: Session, user: User, user_update: UserUpdate
    ) -> User:
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
