# Business-logic layer for the Company aggregate.
#
# Owns company normalization and the get-or-create dedup rule so scrapers and
# other callers can't create duplicate companies for the same normalized name.

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.company import Company
from app.repositories.company_repository import CompanyRepository
from app.utils.normalization import normalize_company_name


class CompanyService:
    def __init__(self, company_repository: CompanyRepository | None = None) -> None:
        self.company_repository = company_repository or CompanyRepository()

    def get_company_by_id(
        self, db: Session, company_id: UUID
    ) -> Company | None:
        return self.company_repository.get_by_id(db, company_id)

    def list_companies(
        self, db: Session, skip: int = 0, limit: int = 50
    ) -> list[Company]:
        return self.company_repository.list(db, skip=skip, limit=limit)

    def get_or_create_company(
        self, db: Session, name: str, location: str | None = None
    ) -> Company:
        """Return the existing company for this name, or create a new one.

        Dedup is by normalized_name, so "Google GmbH" and "google" resolve to
        the same row.
        """
        normalized_name = normalize_company_name(name)

        existing = self.company_repository.get_by_normalized_name(
            db, normalized_name
        )
        if existing is not None:
            return existing

        company = Company(
            name=name.strip(),
            normalized_name=normalized_name,
            location=location,
        )
        return self.company_repository.create(db, company)
