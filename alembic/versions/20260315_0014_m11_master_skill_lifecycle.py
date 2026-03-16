"""m11 master skill lifecycle

Revision ID: 20260315_0014
Revises: 20260312_0013
Create Date: 2026-03-15 12:00:00.000000

"""

from __future__ import annotations

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260315_0014"
down_revision = "20260312_0013"
branch_labels = None
depends_on = None


def _uuid_str() -> str:
    return str(uuid4())


def upgrade() -> None:
    with op.batch_alter_table("master_skills", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "lifecycle_status",
                sa.Enum(
                    "DRAFT",
                    "ACTIVE",
                    "DEACTIVATED",
                    name="master_skill_lifecycle_status",
                    native_enum=False,
                ),
                nullable=False,
                server_default="ACTIVE",
            )
        )

    op.create_table(
        "node_skill_assignments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("node_id", sa.String(length=36), nullable=False),
        sa.Column("skill_id", sa.String(length=36), nullable=False),
        sa.Column(
            "assignment_source",
            sa.Enum(
                "MANUAL",
                "DEFAULT",
                "FORM_STAGE",
                name="node_skill_assignment_source",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("assigned_by_node_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by_node_id"], ["nodes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["master_skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_id", "skill_id", "assignment_source", name="uq_node_skill_assignments_node_skill_source"),
    )

    connection = op.get_bind()
    connection.execute(sa.text("UPDATE master_skills SET lifecycle_status = 'ACTIVE' WHERE lifecycle_status IS NULL"))

    manager_skill_rows = connection.execute(
        sa.text(
            """
            SELECT id, name
            FROM master_skills
            WHERE name IN ('manage-agent-instructions', 'manage-team-budgets')
            """
        )
    ).mappings()
    manager_ids = [
        row["parent_node_id"]
        for row in connection.execute(
            sa.text("SELECT DISTINCT parent_node_id FROM hierarchy WHERE parent_node_id IS NOT NULL")
        ).mappings()
    ]
    for skill in manager_skill_rows:
        for manager_node_id in manager_ids:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO node_skill_assignments (
                        id,
                        node_id,
                        skill_id,
                        assignment_source,
                        assigned_by_node_id
                    ) VALUES (
                        :id,
                        :node_id,
                        :skill_id,
                        'DEFAULT',
                        NULL
                    )
                    """
                ),
                {
                    "id": _uuid_str(),
                    "node_id": manager_node_id,
                    "skill_id": skill["id"],
                },
            )


def downgrade() -> None:
    op.drop_table("node_skill_assignments")
    with op.batch_alter_table("master_skills", schema=None) as batch_op:
        batch_op.drop_column("lifecycle_status")
