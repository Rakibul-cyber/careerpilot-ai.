"""create interview_preparations table

Revision ID: 9a7c4d2e5f31
Revises: d4f2a9c7e1b0
Create Date: 2026-07-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9a7c4d2e5f31'
down_revision: Union[str, Sequence[str], None] = 'd4f2a9c7e1b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


interview_preparation_status = postgresql.ENUM(
    "pending",
    "completed",
    "failed",
    name="interview_preparation_status",
)

interview_difficulty = postgresql.ENUM(
    "easy",
    "medium",
    "hard",
    name="interview_difficulty",
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    interview_preparation_status.create(bind, checkfirst=True)
    interview_difficulty.create(bind, checkfirst=True)

    op.create_table(
        'interview_preparations',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column(
            'generation_status',
            postgresql.ENUM(
                'pending',
                'completed',
                'failed',
                name='interview_preparation_status',
                create_type=False,
            ),
            server_default='pending',
            nullable=False,
        ),
        sa.Column('generation_error', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column(
            'strengths',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            'weaknesses',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            'technical_questions',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            'behavioral_questions',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            'company_questions',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            'study_topics',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            'interview_tips',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            'estimated_difficulty',
            postgresql.ENUM(
                'easy',
                'medium',
                'hard',
                name='interview_difficulty',
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column('raw_ai_response', sa.Text(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ['application_id'], ['applications.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_interview_preparations_id', 'interview_preparations', ['id'])
    op.create_index(
        'ix_interview_preparations_user_id',
        'interview_preparations',
        ['user_id'],
    )
    op.create_index(
        'ix_interview_preparations_application_id',
        'interview_preparations',
        ['application_id'],
    )
    op.create_index(
        'ix_interview_preparations_generation_status',
        'interview_preparations',
        ['generation_status'],
    )
    op.create_index(
        'uq_interview_preparations_application_id',
        'interview_preparations',
        ['application_id'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'uq_interview_preparations_application_id',
        table_name='interview_preparations',
        postgresql_where=sa.text('deleted_at IS NULL'),
    )
    op.drop_index(
        'ix_interview_preparations_generation_status',
        table_name='interview_preparations',
    )
    op.drop_index(
        'ix_interview_preparations_application_id',
        table_name='interview_preparations',
    )
    op.drop_index(
        'ix_interview_preparations_user_id',
        table_name='interview_preparations',
    )
    op.drop_index(
        'ix_interview_preparations_id',
        table_name='interview_preparations',
    )
    op.drop_table('interview_preparations')

    bind = op.get_bind()
    interview_difficulty.drop(bind, checkfirst=True)
    interview_preparation_status.drop(bind, checkfirst=True)
