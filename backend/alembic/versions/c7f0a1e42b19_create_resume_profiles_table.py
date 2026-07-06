"""create resume_profiles table

Revision ID: c7f0a1e42b19
Revises: 1bd7bc63dfa8
Create Date: 2026-07-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c7f0a1e42b19'
down_revision: Union[str, Sequence[str], None] = '1bd7bc63dfa8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Native enum, managed explicitly so downgrade also drops the type.
resume_parse_status = postgresql.ENUM(
    "pending", "completed", "failed", name="resume_parse_status"
)


def upgrade() -> None:
    """Upgrade schema."""
    # Create the enum type first; create_type=False on the column prevents
    # create_table from trying to create it a second time.
    resume_parse_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        'resume_profiles',
        sa.Column('resume_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=64), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('skills', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('work_experience', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('education', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('projects', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('certifications', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('languages', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_ai_response', sa.Text(), nullable=True),
        sa.Column('parse_status', postgresql.ENUM('pending', 'completed', 'failed', name='resume_parse_status', create_type=False), server_default='pending', nullable=False),
        sa.Column('parse_error', sa.Text(), nullable=True),
        sa.Column('parsed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_resume_profiles_id', 'resume_profiles', ['id'], unique=False)
    op.create_index('ix_resume_profiles_parse_status', 'resume_profiles', ['parse_status'], unique=False)
    op.create_index('ix_resume_profiles_user_id', 'resume_profiles', ['user_id'], unique=False)
    # Partial unique index: one live profile per resume.
    op.create_index('uq_resume_profiles_resume_id', 'resume_profiles', ['resume_id'], unique=True, postgresql_where=sa.text('deleted_at IS NULL'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_resume_profiles_resume_id', table_name='resume_profiles', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('ix_resume_profiles_user_id', table_name='resume_profiles')
    op.drop_index('ix_resume_profiles_parse_status', table_name='resume_profiles')
    op.drop_index('ix_resume_profiles_id', table_name='resume_profiles')
    op.drop_table('resume_profiles')
    # Drop the enum type once no table references it.
    resume_parse_status.drop(op.get_bind(), checkfirst=True)
