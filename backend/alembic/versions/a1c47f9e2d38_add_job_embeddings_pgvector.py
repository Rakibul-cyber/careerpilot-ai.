"""add job embeddings (pgvector)

Revision ID: a1c47f9e2d38
Revises: f1b3d8a06c22
Create Date: 2026-07-06 13:00:00.000000

Adds the pgvector extension and semantic-search columns to jobs. Fully
reversible: downgrade drops the columns, index, enum, and extension.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1c47f9e2d38'
down_revision: Union[str, Sequence[str], None] = 'f1b3d8a06c22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Must match app.models.job.JOB_EMBEDDING_DIM.
EMBEDDING_DIM = 1536

job_embedding_status = postgresql.ENUM(
    "pending", "completed", "failed", name="job_embedding_status"
)


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    job_embedding_status.create(op.get_bind(), checkfirst=True)

    op.add_column('jobs', sa.Column('embedding', Vector(EMBEDDING_DIM), nullable=True))
    op.add_column('jobs', sa.Column('embedding_model', sa.String(length=100), nullable=True))
    op.add_column(
        'jobs',
        sa.Column(
            'embedding_status',
            postgresql.ENUM('pending', 'completed', 'failed', name='job_embedding_status', create_type=False),
            server_default='pending',
            nullable=False,
        ),
    )
    op.add_column('jobs', sa.Column('embedding_error', sa.Text(), nullable=True))
    op.add_column('jobs', sa.Column('embedded_at', sa.DateTime(timezone=True), nullable=True))

    op.create_index('ix_jobs_embedding_status', 'jobs', ['embedding_status'], unique=False)
    op.create_index(
        'ix_jobs_embedding_hnsw',
        'jobs',
        ['embedding'],
        unique=False,
        postgresql_using='hnsw',
        postgresql_ops={'embedding': 'vector_cosine_ops'},
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_jobs_embedding_hnsw', table_name='jobs', postgresql_using='hnsw')
    op.drop_index('ix_jobs_embedding_status', table_name='jobs')
    op.drop_column('jobs', 'embedded_at')
    op.drop_column('jobs', 'embedding_error')
    op.drop_column('jobs', 'embedding_status')
    op.drop_column('jobs', 'embedding_model')
    op.drop_column('jobs', 'embedding')
    job_embedding_status.drop(op.get_bind(), checkfirst=True)
    # Drop the extension last, once no column references the vector type.
    op.execute("DROP EXTENSION IF EXISTS vector")
