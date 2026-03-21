"""m13a_retry_and_failure_telemetry

Revision ID: 20260319_0015
Revises: 20260315_0014
Create Date: 2026-03-19 08:55:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '20260319_0015'
down_revision = '20260315_0014'
branch_labels = None
depends_on = None


retry_failure_class = sa.Enum(
    'transient',
    'budget_recoverable',
    'terminal',
    name='retry_failure_class',
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        'agent_task_retries',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('node_id', sa.String(length=36), nullable=False),
        sa.Column('task_key', sa.String(length=255), nullable=False),
        sa.Column('session_key', sa.String(length=255), nullable=True),
        sa.Column('provider', sa.String(length=255), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('failure_class', retry_failure_class, nullable=False),
        sa.Column('status', sa.String(length=64), server_default='pending', nullable=False),
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('last_run_id', sa.String(length=64), nullable=True),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_key', name='uq_agent_task_retries_task_key'),
    )
    op.create_table(
        'agent_llm_failure_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('node_id', sa.String(length=36), nullable=False),
        sa.Column('task_retry_id', sa.String(length=36), nullable=True),
        sa.Column('session_key', sa.String(length=255), nullable=True),
        sa.Column('task_key', sa.String(length=255), nullable=True),
        sa.Column('provider', sa.String(length=255), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('failure_class', retry_failure_class, nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_retry_id'], ['agent_task_retries.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('agent_llm_failure_events')
    op.drop_table('agent_task_retries')
    retry_failure_class.drop(op.get_bind(), checkfirst=False)
