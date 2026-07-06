"""create job_recommendations table

Revision ID: b2d59e83f471
Revises: a1c47f9e2d38
Create Date: 2026-07-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2d59e83f471'
down_revision: Union[str, Sequence[str], None] = 'a1c47f9e2d38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'job_recommendations',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('resume_profile_id', sa.UUID(), nullable=False),
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('job_match_id', sa.UUID(), nullable=True),
        sa.Column('semantic_score', sa.Float(), nullable=False),
        sa.Column('match_score', sa.Float(), nullable=False),
        sa.Column('final_score', sa.Float(), nullable=False),
        sa.Column('recommendation_reasons', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('risk_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_recommendation_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recommended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resume_profile_id'], ['resume_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_match_id'], ['job_matches.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_job_recommendations_id', 'job_recommendations', ['id'], unique=False)
    op.create_index('ix_job_recommendations_job_id', 'job_recommendations', ['job_id'], unique=False)
    op.create_index('ix_job_recommendations_resume_profile_id', 'job_recommendations', ['resume_profile_id'], unique=False)
    op.create_index('ix_job_recommendations_user_id', 'job_recommendations', ['user_id'], unique=False)
    op.create_index('uq_job_recommendations_profile_job', 'job_recommendations', ['resume_profile_id', 'job_id'], unique=True, postgresql_where=sa.text('deleted_at IS NULL'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_job_recommendations_profile_job', table_name='job_recommendations', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('ix_job_recommendations_user_id', table_name='job_recommendations')
    op.drop_index('ix_job_recommendations_resume_profile_id', table_name='job_recommendations')
    op.drop_index('ix_job_recommendations_job_id', table_name='job_recommendations')
    op.drop_index('ix_job_recommendations_id', table_name='job_recommendations')
    op.drop_table('job_recommendations')
