"""m10a budget precision fix

Revision ID: 20260312_0013
Revises: 20260308_0012
Create Date: 2026-03-12 14:20:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260312_0013"
down_revision = "20260308_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("budgets", schema=None) as batch_op:
        batch_op.alter_column(
            "daily_limit_usd",
            existing_type=sa.Numeric(10, 2),
            type_=sa.Numeric(12, 6),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "per_task_cap_usd",
            existing_type=sa.Numeric(10, 2),
            type_=sa.Numeric(12, 6),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "current_daily_allowance",
            existing_type=sa.Numeric(10, 2),
            type_=sa.Numeric(12, 6),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "rollover_reserve_usd",
            existing_type=sa.Numeric(10, 2),
            type_=sa.Numeric(12, 6),
            existing_nullable=False,
            existing_server_default="0.00",
            server_default="0.000000",
        )
        batch_op.alter_column(
            "current_spend",
            existing_type=sa.Numeric(10, 2),
            type_=sa.Numeric(12, 6),
            existing_nullable=False,
        )

    with op.batch_alter_table("budget_cycles", schema=None) as batch_op:
        batch_op.alter_column(
            "company_budget_usd",
            existing_type=sa.Numeric(10, 2),
            type_=sa.Numeric(12, 6),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("budget_cycles", schema=None) as batch_op:
        batch_op.alter_column(
            "company_budget_usd",
            existing_type=sa.Numeric(12, 6),
            type_=sa.Numeric(10, 2),
            existing_nullable=False,
        )

    with op.batch_alter_table("budgets", schema=None) as batch_op:
        batch_op.alter_column(
            "current_spend",
            existing_type=sa.Numeric(12, 6),
            type_=sa.Numeric(10, 2),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "rollover_reserve_usd",
            existing_type=sa.Numeric(12, 6),
            type_=sa.Numeric(10, 2),
            existing_nullable=False,
            existing_server_default="0.000000",
            server_default="0.00",
        )
        batch_op.alter_column(
            "current_daily_allowance",
            existing_type=sa.Numeric(12, 6),
            type_=sa.Numeric(10, 2),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "per_task_cap_usd",
            existing_type=sa.Numeric(12, 6),
            type_=sa.Numeric(10, 2),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "daily_limit_usd",
            existing_type=sa.Numeric(12, 6),
            type_=sa.Numeric(10, 2),
            existing_nullable=False,
        )
