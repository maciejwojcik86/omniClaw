"""m06 forms state machine registry and events

Revision ID: 20260303_0006
Revises: 20260303_0005
Create Date: 2026-03-03

"""

from __future__ import annotations

from datetime import datetime
import json
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260303_0006"
down_revision = "20260303_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "form_types",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("type_key", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=16), nullable=False, server_default="DRAFT"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("workflow_graph", sa.Text(), nullable=False),
        sa.Column("stage_metadata", sa.Text(), nullable=False),
        sa.Column("validation_errors", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("type_key", "version", name="uq_form_types_type_key_version"),
    )

    op.create_table(
        "form_transition_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("form_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=64), nullable=True),
        sa.Column("to_status", sa.String(length=64), nullable=False),
        sa.Column("decision_key", sa.String(length=64), nullable=True),
        sa.Column("actor_node_id", sa.String(length=36), nullable=True),
        sa.Column("previous_holder_node_id", sa.String(length=36), nullable=True),
        sa.Column("new_holder_node_id", sa.String(length=36), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["form_id"], ["forms_ledger.form_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_node_id"], ["nodes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["previous_holder_node_id"], ["nodes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["new_holder_node_id"], ["nodes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("form_id", "sequence", name="uq_form_transition_events_form_sequence"),
    )

    with op.batch_alter_table("forms_ledger") as batch_op:
        batch_op.add_column(sa.Column("form_type_key", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("form_type_version", sa.String(length=32), nullable=True))
        batch_op.alter_column("type", existing_type=sa.String(length=32), type_=sa.String(length=128), existing_nullable=False)
        batch_op.alter_column(
            "current_status",
            existing_type=sa.String(length=16),
            type_=sa.String(length=64),
            existing_nullable=False,
        )

    bind = op.get_bind()

    bind.execute(sa.text("UPDATE forms_ledger SET type = lower(type) WHERE type IS NOT NULL"))
    bind.execute(
        sa.text(
            "UPDATE forms_ledger "
            "SET form_type_key = CASE "
            "WHEN form_type_key IS NOT NULL THEN form_type_key "
            "WHEN type IS NULL OR type = '' THEN 'message' "
            "ELSE lower(type) "
            "END"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE forms_ledger "
            "SET form_type_version = COALESCE(form_type_version, '1.0.0')"
        )
    )

    workflow_graph = {
        "initial_status": "SENT",
        "edges": [
            {
                "from": "SENT",
                "to": "ARCHIVED",
                "decision": "acknowledge_read",
                "next_holder": {"strategy": "none"},
            },
        ],
    }
    stage_metadata = {
        "SENT": {
            "stage_skill_ref": ".codex/skills/read-and-acknowledge-messages/SKILL.md",
            "stage_template_ref": "templates/forms/message/sent.md",
        },
        "ARCHIVED": {
            "stage_skill_ref": ".codex/skills/read-and-acknowledge-messages/SKILL.md",
            "stage_template_ref": "templates/forms/message/archived.md",
        },
        "DEAD_LETTER": {
            "stage_skill_ref": ".codex/skills/send_message/SKILL.md",
            "stage_template_ref": "templates/forms/message/dead_letter.md",
        },
    }

    existing = bind.execute(
        sa.text(
            "SELECT id FROM form_types WHERE type_key = :type_key AND version = :version"
        ),
        {"type_key": "message", "version": "1.0.0"},
    ).fetchone()
    if existing is None:
        bind.execute(
            sa.text(
                "INSERT INTO form_types "
                "(id, type_key, version, lifecycle_state, description, workflow_graph, stage_metadata) "
                "VALUES (:id, :type_key, :version, :state, :description, :workflow_graph, :stage_metadata)"
            ),
            {
                "id": str(uuid4()),
                "type_key": "message",
                "version": "1.0.0",
                "state": "ACTIVE",
                "description": "Built-in MESSAGE workflow",
                "workflow_graph": json.dumps(workflow_graph),
                "stage_metadata": json.dumps(stage_metadata),
            },
        )
    else:
        bind.execute(
            sa.text(
                "UPDATE form_types SET lifecycle_state = 'ACTIVE', workflow_graph = :workflow_graph, "
                "stage_metadata = :stage_metadata WHERE type_key = :type_key AND version = :version"
            ),
            {
                "workflow_graph": json.dumps(workflow_graph),
                "stage_metadata": json.dumps(stage_metadata),
                "type_key": "message",
                "version": "1.0.0",
            },
        )

    rows = bind.execute(
        sa.text(
            "SELECT form_id, current_status, current_holder_node, sender_node_id, target_node_id, history_log, created_at "
            "FROM forms_ledger ORDER BY created_at ASC"
        )
    ).fetchall()

    for row in rows:
        history_entries: list[dict[str, object]] = []
        if row.history_log:
            try:
                parsed = json.loads(row.history_log)
                if isinstance(parsed, list):
                    history_entries = [item for item in parsed if isinstance(item, dict)]
            except json.JSONDecodeError:
                history_entries = []

        if not history_entries:
            history_entries = [{"status": row.current_status, "at": None}]

        previous_status = None
        previous_holder = None
        sequence = 1
        for item in history_entries:
            to_status = str(item.get("status") or row.current_status)
            at_raw = item.get("at")
            created_at = _safe_datetime(at_raw) or _safe_datetime(row.created_at) or datetime.utcnow()

            new_holder = row.current_holder_node
            if to_status in {"DELIVERED", "ARCHIVED"} and row.target_node_id:
                new_holder = row.target_node_id
            elif to_status == "DEAD_LETTER" and row.sender_node_id:
                new_holder = row.sender_node_id

            bind.execute(
                sa.text(
                    "INSERT INTO form_transition_events "
                    "(id, form_id, sequence, from_status, to_status, decision_key, actor_node_id, "
                    "previous_holder_node_id, new_holder_node_id, payload_json, created_at) "
                    "VALUES (:id, :form_id, :sequence, :from_status, :to_status, :decision_key, :actor_node_id, "
                    ":previous_holder_node_id, :new_holder_node_id, :payload_json, :created_at)"
                ),
                {
                    "id": str(uuid4()),
                    "form_id": row.form_id,
                    "sequence": sequence,
                    "from_status": previous_status,
                    "to_status": to_status,
                    "decision_key": None,
                    "actor_node_id": row.sender_node_id,
                    "previous_holder_node_id": previous_holder,
                    "new_holder_node_id": new_holder,
                    "payload_json": json.dumps({"source": "history_log_backfill"}),
                    "created_at": created_at,
                },
            )
            previous_status = to_status
            previous_holder = new_holder
            sequence += 1


def downgrade() -> None:
    with op.batch_alter_table("forms_ledger") as batch_op:
        batch_op.alter_column("current_status", existing_type=sa.String(length=64), type_=sa.String(length=16), existing_nullable=False)
        batch_op.alter_column("type", existing_type=sa.String(length=128), type_=sa.String(length=32), existing_nullable=False)
        batch_op.drop_column("form_type_version")
        batch_op.drop_column("form_type_key")

    op.drop_table("form_transition_events")
    op.drop_table("form_types")


def _safe_datetime(raw: object) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None
