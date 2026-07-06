"""create applications table

Revision ID: d4f2a9c7e1b0
Revises: b2d59e83f471
Create Date: 2026-07-07 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4f2a9c7e1b0'
down_revision: Union[str, Sequence[str], None] = 'b2d59e83f471'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


application_status = postgresql.ENUM(
    "draft",
    "ready",
    "applied",
    "viewed",
    "phone_screen",
    "technical_interview",
    "hr_interview",
    "final_interview",
    "offer",
    "accepted",
    "rejected",
    "withdrawn",
    name="application_status",
)

application_source = postgresql.ENUM(
    "manual",
    "recommendation",
    "job_alert",
    "external_import",
    name="application_source",
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    application_status.create(bind, checkfirst=True)
    application_source.create(bind, checkfirst=True)

    op.create_table(
        'applications',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('resume_profile_id', sa.UUID(), nullable=False),
        sa.Column('cover_letter_id', sa.UUID(), nullable=True),
        sa.Column('job_recommendation_id', sa.UUID(), nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM(
                'draft',
                'ready',
                'applied',
                'viewed',
                'phone_screen',
                'technical_interview',
                'hr_interview',
                'final_interview',
                'offer',
                'accepted',
                'rejected',
                'withdrawn',
                name='application_status',
                create_type=False,
            ),
            server_default='draft',
            nullable=False,
        ),
        sa.Column(
            'source',
            postgresql.ENUM(
                'manual',
                'recommendation',
                'job_alert',
                'external_import',
                name='application_source',
                create_type=False,
            ),
            server_default='manual',
            nullable=False,
        ),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'last_status_change_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('company_response', sa.Text(), nullable=True),
        sa.Column('interview_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('offer_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('follow_up_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['resume_profile_id'],
            ['resume_profiles.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['cover_letter_id'],
            ['cover_letters.id'],
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['job_recommendation_id'],
            ['job_recommendations.id'],
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_applications_id', 'applications', ['id'])
    op.create_index('ix_applications_user_id', 'applications', ['user_id'])
    op.create_index('ix_applications_job_id', 'applications', ['job_id'])
    op.create_index(
        'ix_applications_resume_profile_id',
        'applications',
        ['resume_profile_id'],
    )
    op.create_index('ix_applications_status', 'applications', ['status'])
    op.create_index('ix_applications_source', 'applications', ['source'])
    op.create_index('ix_applications_created_at', 'applications', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_applications_created_at', table_name='applications')
    op.drop_index('ix_applications_source', table_name='applications')
    op.drop_index('ix_applications_status', table_name='applications')
    op.drop_index(
        'ix_applications_resume_profile_id',
        table_name='applications',
    )
    op.drop_index('ix_applications_job_id', table_name='applications')
    op.drop_index('ix_applications_user_id', table_name='applications')
    op.drop_index('ix_applications_id', table_name='applications')
    op.drop_table('applications')

    bind = op.get_bind()
    application_source.drop(bind, checkfirst=True)
    application_status.drop(bind, checkfirst=True)
