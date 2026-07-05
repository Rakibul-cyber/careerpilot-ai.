"""add pg_trgm and gin trigram indexes for search

Revision ID: 8c18594ccbc3
Revises: 310801ab4e96
Create Date: 2026-07-05 12:48:38.444897

Enables the pg_trgm extension and adds GIN trigram indexes on the columns that
JobRepository.search matches with ILIKE '%...%'. These let PostgreSQL use an
index for substring/fuzzy matches instead of a sequential scan on large tables.
No schema or data changes; existing B-tree indexes are kept untouched.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c18594ccbc3'
down_revision: Union[str, Sequence[str], None] = '310801ab4e96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (index_name, table, column) for every column matched by ILIKE in search().
_TRGM_INDEXES = [
    ("ix_jobs_normalized_title_trgm", "jobs", "normalized_title"),
    ("ix_jobs_description_trgm", "jobs", "description"),
    ("ix_jobs_requirements_trgm", "jobs", "requirements"),
    ("ix_jobs_location_trgm", "jobs", "location"),
    ("ix_companies_name_trgm", "companies", "name"),
    ("ix_companies_normalized_name_trgm", "companies", "normalized_name"),
]


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for index_name, table, column in _TRGM_INDEXES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {index_name} "
            f"ON {table} USING gin ({column} gin_trgm_ops)"
        )


def downgrade() -> None:
    """Downgrade schema."""
    for index_name, _table, _column in _TRGM_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
    # Drop the extension we created; the trigram indexes above are gone, so
    # nothing depends on it anymore.
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
