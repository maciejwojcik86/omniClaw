"""m04 enforce single line manager and plaintext password field

Revision ID: 20260301_0003
Revises: 20260301_0002
Create Date: 2026-03-01

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260301_0003"
down_revision = "20260301_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("nodes") as batch_op:
        batch_op.alter_column(
            "linux_password_hash",
            new_column_name="linux_password",
            existing_type=sa.String(length=255),
            existing_nullable=True,
        )

    # Legacy hash values cannot be converted back to plaintext; clear them after rename.
    op.execute(
        sa.text("UPDATE nodes SET linux_password = NULL WHERE linux_password LIKE 'pbkdf2_sha256$%'")
    )

    with op.batch_alter_table("hierarchy") as batch_op:
        batch_op.create_unique_constraint("uq_hierarchy_child_manager", ["child_node_id"])


def downgrade() -> None:
    with op.batch_alter_table("hierarchy") as batch_op:
        batch_op.drop_constraint("uq_hierarchy_child_manager", type_="unique")

    with op.batch_alter_table("nodes") as batch_op:
        batch_op.alter_column(
            "linux_password",
            new_column_name="linux_password_hash",
            existing_type=sa.String(length=255),
            existing_nullable=True,
        )
