"""add jobs full text search

Revision ID: a3d134ee3d15
Revises: 8c18594ccbc3
Create Date: 2026-07-05 13:35:24.476276

Adds a trigger-maintained ``search_vector`` tsvector column to ``jobs`` for
relevance-ranked full-text search, plus a GIN index over it. Weights: title /
normalized_title = A, description / requirements = B, location = C. The column
is kept up to date by a BEFORE INSERT/UPDATE trigger, so application code never
sets it. Existing rows are backfilled. No existing columns or behavior change.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3d134ee3d15'
down_revision: Union[str, Sequence[str], None] = '8c18594ccbc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The weighted tsvector expression, shared by the trigger and the backfill.
_SEARCH_VECTOR_SQL = """
    setweight(to_tsvector('english', coalesce({title}, '')), 'A') ||
    setweight(to_tsvector('english', coalesce({normalized_title}, '')), 'A') ||
    setweight(to_tsvector('english', coalesce({description}, '')), 'B') ||
    setweight(to_tsvector('english', coalesce({requirements}, '')), 'B') ||
    setweight(to_tsvector('english', coalesce({location}, '')), 'C')
"""


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Nullable tsvector column (trigger-maintained, not app-maintained).
    op.execute("ALTER TABLE jobs ADD COLUMN search_vector tsvector")

    # 2. Trigger function that (re)builds the weighted vector from NEW.*.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION jobs_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
          NEW.search_vector :=
        """
        + _SEARCH_VECTOR_SQL.format(
            title="NEW.title",
            normalized_title="NEW.normalized_title",
            description="NEW.description",
            requirements="NEW.requirements",
            location="NEW.location",
        )
        + """;
          RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """
    )

    # 3. Fire the function whenever a searchable column changes.
    op.execute(
        """
        CREATE TRIGGER jobs_search_vector_trigger
        BEFORE INSERT OR UPDATE OF title, normalized_title, description,
                                   requirements, location
        ON jobs
        FOR EACH ROW
        EXECUTE FUNCTION jobs_search_vector_update()
        """
    )

    # 4. Backfill existing rows.
    op.execute(
        "UPDATE jobs SET search_vector = "
        + _SEARCH_VECTOR_SQL.format(
            title="title",
            normalized_title="normalized_title",
            description="description",
            requirements="requirements",
            location="location",
        )
    )

    # 5. GIN index for fast @@ matching / ranking.
    op.execute(
        "CREATE INDEX ix_jobs_search_vector_gin "
        "ON jobs USING gin (search_vector)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_jobs_search_vector_gin")
    op.execute("DROP TRIGGER IF EXISTS jobs_search_vector_trigger ON jobs")
    op.execute("DROP FUNCTION IF EXISTS jobs_search_vector_update()")
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS search_vector")
