"""m07 add optimistic lock version to forms_ledger

Revision ID: 20260305_0008
Revises: 20260303_0007
Create Date: 2026-03-05

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260305_0008"
down_revision = "20260303_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("forms_ledger") as batch_op:
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    with op.batch_alter_table("forms_ledger") as batch_op:
        batch_op.drop_column("version")
