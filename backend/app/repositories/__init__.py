# repositories package.
# Data-access layer. Wraps all persistence operations (CRUD/queries) behind a
# stable interface so services never touch SQLAlchemy directly. This keeps the
# storage engine swappable and makes the business layer trivially unit-testable.

from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.repositories.user_repository import UserRepository

__all__ = ["UserRepository", "CompanyRepository", "JobRepository"]
