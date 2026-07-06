"""create job_matches table

Revision ID: e4a9c2d17b60
Revises: c7f0a1e42b19
Create Date: 2026-07-06 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e4a9c2d17b60'
down_revision: Union[str, Sequence[str], None] = 'c7f0a1e42b19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'job_matches',
        sa.Column('resume_profile_id', sa.UUID(), nullable=False),
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('skill_score', sa.Float(), nullable=False),
        sa.Column('title_score', sa.Float(), nullable=False),
        sa.Column('location_score', sa.Float(), nullable=False),
        sa.Column('experience_score', sa.Float(), nullable=False),
        sa.Column('matched_skills', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('missing_skills', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('match_reasons', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('risk_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_match_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('matched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['resume_profile_id'], ['resume_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_job_matches_id', 'job_matches', ['id'], unique=False)
    op.create_index('ix_job_matches_job_id', 'job_matches', ['job_id'], unique=False)
    op.create_index('ix_job_matches_resume_profile_id', 'job_matches', ['resume_profile_id'], unique=False)
    op.create_index('ix_job_matches_user_id', 'job_matches', ['user_id'], unique=False)
    # Partial unique index: one live match per (resume_profile, job).
    op.create_index('uq_job_matches_profile_job', 'job_matches', ['resume_profile_id', 'job_id'], unique=True, postgresql_where=sa.text('deleted_at IS NULL'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_job_matches_profile_job', table_name='job_matches', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('ix_job_matches_user_id', table_name='job_matches')
    op.drop_index('ix_job_matches_resume_profile_id', table_name='job_matches')
    op.drop_index('ix_job_matches_job_id', table_name='job_matches')
    op.drop_index('ix_job_matches_id', table_name='job_matches')
    op.drop_table('job_matches')
