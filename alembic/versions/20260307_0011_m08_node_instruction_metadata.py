"""m08 node instruction metadata

Revision ID: 20260307_0011
Revises: 20260306_0010
Create Date: 2026-03-07

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260307_0011"
down_revision = "20260306_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("nodes") as batch:
        batch.add_column(sa.Column("role_name", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("instruction_template_root", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("nodes") as batch:
        batch.drop_column("instruction_template_root")
        batch.drop_column("role_name")
