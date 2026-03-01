"""m02 canonical state schema

Revision ID: 20260301_0001
Revises:
Create Date: 2026-03-01

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260301_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nodes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("linux_uid", sa.Integer(), nullable=True),
        sa.Column("autonomy_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "hierarchy",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("parent_node_id", sa.String(length=36), nullable=False),
        sa.Column("child_node_id", sa.String(length=36), nullable=False),
        sa.Column("relationship_type", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["child_node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_node_id", "child_node_id", name="uq_hierarchy_parent_child"),
    )

    op.create_table(
        "budgets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("node_id", sa.String(length=36), nullable=False),
        sa.Column("daily_limit_usd", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("per_task_cap_usd", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("virtual_api_key", sa.String(length=255), nullable=True),
        sa.Column("parent_node_id", sa.String(length=36), nullable=True),
        sa.Column("allocated_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("current_daily_allowance", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("current_spend", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_node_id"], ["nodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_id"),
    )

    op.create_table(
        "forms_ledger",
        sa.Column("form_id", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("current_status", sa.String(length=16), nullable=False),
        sa.Column("current_holder_node", sa.String(length=36), nullable=True),
        sa.Column("history_log", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["current_holder_node"], ["nodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("form_id"),
    )

    op.create_table(
        "master_skills",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("execution_endpoint", sa.String(length=255), nullable=True),
        sa.Column("validation_status", sa.String(length=16), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False, server_default="0.1.0"),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table("master_skills")
    op.drop_table("forms_ledger")
    op.drop_table("budgets")
    op.drop_table("hierarchy")
    op.drop_table("nodes")
