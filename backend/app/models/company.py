# Company entity — the employer a job listing belongs to.
#
# normalized_name is the dedup key: a lowercased/cleaned form of name so that
# "Acme, Inc." and "acme inc" collapse to a single company row.

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import BaseModel


class Company(BaseModel, Base):
    __tablename__ = "companies"
    __table_args__ = (
        # GIN trigram indexes backing the ILIKE '%...%' company matches in
        # JobRepository.search (created via migration 8c18594ccbc3).
        Index(
            "ix_companies_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "ix_companies_normalized_name_trgm",
            "normalized_name",
            postgresql_using="gin",
            postgresql_ops={"normalized_name": "gin_trgm_ops"},
        ),
    )

    # Human-readable company name as sourced.
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Canonical dedup key; unique so each real company maps to one row.
    normalized_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    career_page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
