"""create cover_letters table

Revision ID: f1b3d8a06c22
Revises: e4a9c2d17b60
Create Date: 2026-07-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f1b3d8a06c22'
down_revision: Union[str, Sequence[str], None] = 'e4a9c2d17b60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Native enum, managed explicitly so downgrade also drops the type.
cover_letter_status = postgresql.ENUM(
    "pending", "completed", "failed", name="cover_letter_status"
)


def upgrade() -> None:
    """Upgrade schema."""
    cover_letter_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        'cover_letters',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('resume_profile_id', sa.UUID(), nullable=False),
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('job_match_id', sa.UUID(), nullable=True),
        sa.Column('language', sa.String(length=16), server_default='en', nullable=False),
        sa.Column('tone', sa.String(length=32), server_default='professional', nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('generation_status', postgresql.ENUM('pending', 'completed', 'failed', name='cover_letter_status', create_type=False), server_default='pending', nullable=False),
        sa.Column('generation_error', sa.Text(), nullable=True),
        sa.Column('raw_ai_response', sa.Text(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
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
    op.create_index('ix_cover_letters_generation_status', 'cover_letters', ['generation_status'], unique=False)
    op.create_index('ix_cover_letters_id', 'cover_letters', ['id'], unique=False)
    op.create_index('ix_cover_letters_job_id', 'cover_letters', ['job_id'], unique=False)
    op.create_index('ix_cover_letters_resume_profile_id', 'cover_letters', ['resume_profile_id'], unique=False)
    op.create_index('ix_cover_letters_user_id', 'cover_letters', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_cover_letters_user_id', table_name='cover_letters')
    op.drop_index('ix_cover_letters_resume_profile_id', table_name='cover_letters')
    op.drop_index('ix_cover_letters_job_id', table_name='cover_letters')
    op.drop_index('ix_cover_letters_id', table_name='cover_letters')
    op.drop_index('ix_cover_letters_generation_status', table_name='cover_letters')
    op.drop_table('cover_letters')
    cover_letter_status.drop(op.get_bind(), checkfirst=True)
