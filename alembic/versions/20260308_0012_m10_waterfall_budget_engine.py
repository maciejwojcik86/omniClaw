"""m10 waterfall budget engine

Revision ID: 20260308_0012
Revises: b1fd009b766f
Create Date: 2026-03-08 13:45:00.000000

"""
from __future__ import annotations

from decimal import Decimal

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260308_0012"
down_revision = "b1fd009b766f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("budgets", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "budget_mode",
                sa.Enum("metered", "free", name="budget_mode", native_enum=False),
                nullable=False,
                server_default="metered",
            )
        )
        batch_op.add_column(
            sa.Column("rollover_reserve_usd", sa.Numeric(10, 2), nullable=False, server_default="0.00")
        )
        batch_op.add_column(sa.Column("review_required_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "budget_allocations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("manager_node_id", sa.String(length=36), nullable=False),
        sa.Column("child_node_id", sa.String(length=36), nullable=False),
        sa.Column("percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["manager_node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["child_node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manager_node_id", "child_node_id", name="uq_budget_allocations_manager_child"),
    )

    op.create_table(
        "budget_cycles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("cycle_date", sa.Date(), nullable=False),
        sa.Column("company_budget_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("root_allocator_node_id", sa.String(length=36), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["root_allocator_node_id"], ["nodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cycle_date", name="uq_budget_cycles_cycle_date"),
    )

    connection = op.get_bind()
    connection.execute(sa.text("UPDATE budgets SET budget_mode = 'metered' WHERE budget_mode IS NULL"))
    connection.execute(sa.text("UPDATE budgets SET rollover_reserve_usd = 0.00 WHERE rollover_reserve_usd IS NULL"))

    hierarchy_rows = connection.execute(
        sa.text("SELECT parent_node_id, child_node_id FROM hierarchy")
    ).mappings()
    for row in hierarchy_rows:
        connection.execute(
            sa.text(
                "UPDATE budgets "
                "SET parent_node_id = :parent_node_id "
                "WHERE node_id = :child_node_id AND parent_node_id IS NULL"
            ),
            {
                "parent_node_id": row["parent_node_id"],
                "child_node_id": row["child_node_id"],
            },
        )


def downgrade() -> None:
    op.drop_table("budget_cycles")
    op.drop_table("budget_allocations")
    with op.batch_alter_table("budgets", schema=None) as batch_op:
        batch_op.drop_column("review_required_at")
        batch_op.drop_column("rollover_reserve_usd")
        batch_op.drop_column("budget_mode")
