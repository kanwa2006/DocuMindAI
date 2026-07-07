"""add_eval_tables

Revision ID: 1a2b3c4d5e60
Revises: a1b2c3d4e5f6
Create Date: 2026-05-19 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = '1a2b3c4d5e60'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'eval_benchmark_queries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('query_text', sa.String(), nullable=False),
        sa.Column('expected_doc_id', UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('expected_page', sa.Integer(), nullable=True),
        sa.Column('expected_answer_excerpt', sa.String(), nullable=True),
        sa.Column('query_type', sa.String(), nullable=False, server_default='human_reviewed'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_eval_benchmark_workspace_id', 'eval_benchmark_queries', ['workspace_id'])
    op.create_index('ix_eval_benchmark_is_active', 'eval_benchmark_queries', ['is_active'])

    op.create_table(
        'eval_results',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', UUID(as_uuid=True), nullable=False),
        sa.Column('benchmark_query_id', UUID(as_uuid=True), sa.ForeignKey('eval_benchmark_queries.id', ondelete='SET NULL'), nullable=True),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('precision_at_5', sa.Float(), nullable=True),
        sa.Column('recall_at_5', sa.Float(), nullable=True),
        sa.Column('citation_correct', sa.Boolean(), nullable=True),
        sa.Column('hallucination_detected', sa.Boolean(), nullable=True),
        sa.Column('top_chunks_retrieved', JSONB(), nullable=True),
        sa.Column('grounded_answer_valid', sa.Boolean(), nullable=True),
        sa.Column('reranker_delta', sa.Float(), nullable=True),
        sa.Column('retrieval_latency_ms', sa.Integer(), nullable=True),
        sa.Column('triggered_by', sa.String(), nullable=False, server_default='manual'),
        sa.Column('model_version', sa.String(), nullable=True),
        sa.Column('chunking_version', sa.String(), nullable=True),
        sa.Column('run_timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('notes', sa.String(), nullable=True),
    )
    op.create_index('ix_eval_results_workspace_run_ts', 'eval_results', ['workspace_id', 'run_timestamp'])
    op.create_index('ix_eval_results_run_id', 'eval_results', ['run_id'])
    op.create_index('ix_eval_results_benchmark_query_id', 'eval_results', ['benchmark_query_id'])


def downgrade() -> None:
    op.drop_table('eval_results')
    op.drop_table('eval_benchmark_queries')
