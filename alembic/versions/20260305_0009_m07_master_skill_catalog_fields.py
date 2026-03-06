"""m07 master skill catalog fields

Revision ID: 20260305_0009
Revises: 20260305_0008
Create Date: 2026-03-05

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260305_0009"
down_revision = "20260305_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("master_skills") as batch:
        batch.add_column(sa.Column("form_type_key", sa.String(length=128), nullable=True))
        batch.add_column(
            sa.Column(
                "master_path",
                sa.String(length=1024),
                nullable=False,
                server_default=sa.text("''"),
            )
        )
        batch.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("master_skills") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("description")
        batch.drop_column("master_path")
        batch.drop_column("form_type_key")
