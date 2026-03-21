"""m13a_retry_request_payload

Revision ID: 20260320_0016
Revises: 20260319_0015
Create Date: 2026-03-20 16:05:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260320_0016"
down_revision = "20260319_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_task_retries",
        sa.Column("request_payload_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_task_retries", "request_payload_json")
