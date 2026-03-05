"""m05 message ledger metadata columns

Revision ID: 20260303_0005
Revises: 20260303_0004
Create Date: 2026-03-03

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260303_0005"
down_revision = "20260303_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("forms_ledger") as batch_op:
        batch_op.add_column(sa.Column("message_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("sender_node_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("target_node_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("subject", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("source_path", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("delivery_path", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("archive_path", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("dead_letter_path", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("routed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("failure_reason", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_forms_ledger_sender_node",
            "nodes",
            ["sender_node_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_forms_ledger_target_node",
            "nodes",
            ["target_node_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("forms_ledger") as batch_op:
        batch_op.drop_constraint("fk_forms_ledger_target_node", type_="foreignkey")
        batch_op.drop_constraint("fk_forms_ledger_sender_node", type_="foreignkey")
        batch_op.drop_column("failure_reason")
        batch_op.drop_column("dead_lettered_at")
        batch_op.drop_column("archived_at")
        batch_op.drop_column("routed_at")
        batch_op.drop_column("queued_at")
        batch_op.drop_column("dead_letter_path")
        batch_op.drop_column("archive_path")
        batch_op.drop_column("delivery_path")
        batch_op.drop_column("source_path")
        batch_op.drop_column("subject")
        batch_op.drop_column("target_node_id")
        batch_op.drop_column("sender_node_id")
        batch_op.drop_column("message_name")
