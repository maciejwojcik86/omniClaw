"""m04 node runtime tracking columns

Revision ID: 20260301_0002
Revises: 20260301_0001
Create Date: 2026-03-01

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260301_0002"
down_revision = "20260301_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("nodes") as batch_op:
        batch_op.add_column(sa.Column("linux_username", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("linux_password_hash", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("workspace_root", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("nullclaw_config_path", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("primary_model", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("nodes") as batch_op:
        batch_op.drop_column("primary_model")
        batch_op.drop_column("nullclaw_config_path")
        batch_op.drop_column("workspace_root")
        batch_op.drop_column("linux_password_hash")
        batch_op.drop_column("linux_username")
