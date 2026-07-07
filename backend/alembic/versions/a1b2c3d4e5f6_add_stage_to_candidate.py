"""add_stage_to_candidate

Revision ID: a1b2c3d4e5f6
Revises: f1e2d3c4b5a6
Create Date: 2026-05-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f1e2d3c4b5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('hr_candidates',
        sa.Column('stage', sa.String(), nullable=True, server_default='applied'))
    op.add_column('hr_job_matches',
        sa.Column('semantic_score', sa.Float(), nullable=True))
    op.add_column('hr_job_matches',
        sa.Column('final_score', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('hr_job_matches', 'final_score')
    op.drop_column('hr_job_matches', 'semantic_score')
    op.drop_column('hr_candidates', 'stage')
