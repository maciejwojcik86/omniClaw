"""m07b nanobot runtime config rename

Revision ID: 20260306_0010
Revises: 20260305_0009
Create Date: 2026-03-06

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260306_0010"
down_revision = "20260305_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("nodes") as batch:
        batch.alter_column(
            "nullclaw_config_path",
            new_column_name="runtime_config_path",
            existing_type=sa.String(length=512),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("nodes") as batch:
        batch.alter_column(
            "runtime_config_path",
            new_column_name="nullclaw_config_path",
            existing_type=sa.String(length=512),
            existing_nullable=True,
        )
