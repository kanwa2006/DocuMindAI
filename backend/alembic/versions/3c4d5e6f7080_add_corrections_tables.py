"""add_corrections_tables

Revision ID: 3c4d5e6f7080
Revises: 2b3c4d5e6f70
Create Date: 2026-05-19 12:32:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = '3c4d5e6f7080'
down_revision: Union[str, None] = '2b3c4d5e6f70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'corrections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', UUID(as_uuid=True), sa.ForeignKey('chat_sessions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('message_id', UUID(as_uuid=True), sa.ForeignKey('chat_messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('issue_type', sa.String(), nullable=False),
        sa.Column('incorrect_excerpt', sa.String(), nullable=True),
        sa.Column('suggested_correction', sa.String(), nullable=True),
        sa.Column('citation_id', sa.String(), nullable=True),
        sa.Column('reporter_confidence', sa.String(), nullable=False, server_default='unsure'),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('reviewer_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('eval_query_created', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_corrections_user_id', 'corrections', ['user_id'])
    op.create_index('ix_corrections_session_id', 'corrections', ['session_id'])
    op.create_index('ix_corrections_workspace_id', 'corrections', ['workspace_id'])
    op.create_index('ix_corrections_status', 'corrections', ['status'])
    op.create_index('ix_corrections_created_at', 'corrections', ['created_at'])

    op.create_table(
        'correction_notes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('correction_id', UUID(as_uuid=True), sa.ForeignKey('corrections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('note_text', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_correction_notes_correction_id', 'correction_notes', ['correction_id'])


def downgrade() -> None:
    op.drop_table('correction_notes')
    op.drop_table('corrections')
