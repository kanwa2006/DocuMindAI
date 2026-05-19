"""add_study_quiz_table

Revision ID: f1e2d3c4b5a6
Revises: 4986fbbf8129
Create Date: 2026-05-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1e2d3c4b5a6'
down_revision: Union[str, None] = '4986fbbf8129'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'study_quizzes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('topic', sa.String(), nullable=False),
        sa.Column('difficulty', sa.String(), nullable=True),
        sa.Column('doc_ids', sa.JSON(), nullable=True),
        sa.Column('questions', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_study_quizzes_id'), 'study_quizzes', ['id'], unique=False)
    op.create_index(op.f('ix_study_quizzes_workspace_id'), 'study_quizzes', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_study_quizzes_workspace_id'), table_name='study_quizzes')
    op.drop_index(op.f('ix_study_quizzes_id'), table_name='study_quizzes')
    op.drop_table('study_quizzes')
