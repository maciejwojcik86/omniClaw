"""m04 gateway runtime state tracking

Revision ID: 20260303_0004
Revises: 20260301_0003
Create Date: 2026-03-03

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260303_0004"
down_revision = "20260301_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("nodes") as batch_op:
        batch_op.add_column(sa.Column("gateway_running", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("gateway_pid", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("gateway_host", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("gateway_port", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("gateway_started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("gateway_stopped_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("nodes") as batch_op:
        batch_op.drop_column("gateway_stopped_at")
        batch_op.drop_column("gateway_started_at")
        batch_op.drop_column("gateway_port")
        batch_op.drop_column("gateway_host")
        batch_op.drop_column("gateway_pid")
        batch_op.drop_column("gateway_running")
