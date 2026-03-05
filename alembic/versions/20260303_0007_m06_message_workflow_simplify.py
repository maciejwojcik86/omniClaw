"""m06 simplify default message workflow

Revision ID: 20260303_0007
Revises: 20260303_0006
Create Date: 2026-03-03

"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260303_0007"
down_revision = "20260303_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, workflow_graph, stage_metadata "
            "FROM form_types WHERE type_key = :type_key AND version = :version"
        ),
        {"type_key": "message", "version": "1.0.0"},
    ).fetchall()

    for row in rows:
        workflow_graph = _parse_json(row.workflow_graph)
        if not _looks_like_legacy_message_graph(workflow_graph):
            continue

        bind.execute(
            sa.text(
                "UPDATE form_types SET description = :description, workflow_graph = :workflow_graph, "
                "stage_metadata = :stage_metadata WHERE id = :id"
            ),
            {
                "id": row.id,
                "description": "Built-in MESSAGE workflow (draft -> waiting_to_be_read -> archived)",
                "workflow_graph": json.dumps(_new_message_workflow_graph()),
                "stage_metadata": json.dumps(_new_message_stage_metadata()),
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, workflow_graph FROM form_types "
            "WHERE type_key = :type_key AND version = :version"
        ),
        {"type_key": "message", "version": "1.0.0"},
    ).fetchall()

    for row in rows:
        workflow_graph = _parse_json(row.workflow_graph)
        if not _looks_like_new_message_graph(workflow_graph):
            continue

        bind.execute(
            sa.text(
                "UPDATE form_types SET description = :description, workflow_graph = :workflow_graph, "
                "stage_metadata = :stage_metadata WHERE id = :id"
            ),
            {
                "id": row.id,
                "description": "Built-in MESSAGE workflow (sent then archived on read acknowledgement)",
                "workflow_graph": json.dumps(_legacy_message_workflow_graph()),
                "stage_metadata": json.dumps(_legacy_message_stage_metadata()),
            },
        )


def _parse_json(raw: object) -> dict[str, object]:
    if not isinstance(raw, str):
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _looks_like_legacy_message_graph(workflow_graph: dict[str, object]) -> bool:
    if workflow_graph.get("initial_status") != "SENT":
        return False
    edges = workflow_graph.get("edges")
    if not isinstance(edges, list):
        return False
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if edge.get("from") == "SENT" and edge.get("to") == "ARCHIVED" and edge.get("decision") == "acknowledge_read":
            return True
    return False


def _looks_like_new_message_graph(workflow_graph: dict[str, object]) -> bool:
    if workflow_graph.get("initial_status") != "DRAFT":
        return False
    edges = workflow_graph.get("edges")
    if not isinstance(edges, list):
        return False
    has_dispatch = False
    has_ack = False
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if (
            edge.get("from") == "DRAFT"
            and edge.get("to") == "WAITING_TO_BE_READ"
            and edge.get("decision") == "dispatch_to_target"
        ):
            has_dispatch = True
        if edge.get("from") == "WAITING_TO_BE_READ" and edge.get("to") == "ARCHIVED" and edge.get("decision") == "acknowledge_read":
            has_ack = True
    return has_dispatch and has_ack


def _new_message_workflow_graph() -> dict[str, object]:
    return {
        "initial_status": "DRAFT",
        "dispatch_decision": "dispatch_to_target",
        "acknowledge_decision": "acknowledge_read",
        "archive_status": "ARCHIVED",
        "edges": [
            {
                "from": "DRAFT",
                "to": "WAITING_TO_BE_READ",
                "decision": "dispatch_to_target",
                "next_holder": {"strategy": "field_ref", "value": "target_node_id"},
            },
            {
                "from": "WAITING_TO_BE_READ",
                "to": "ARCHIVED",
                "decision": "acknowledge_read",
                "next_holder": {"strategy": "none"},
            },
            {
                "from": "SENT",
                "to": "ARCHIVED",
                "decision": "acknowledge_read",
                "next_holder": {"strategy": "none"},
            },
        ],
    }


def _new_message_stage_metadata() -> dict[str, object]:
    return {
        "DRAFT": {
            "stage_skill_ref": ".codex/skills/send_message/SKILL.md",
        },
        "WAITING_TO_BE_READ": {
            "stage_skill_ref": ".codex/skills/read-and-acknowledge-messages/SKILL.md",
        },
        "SENT": {
            "stage_skill_ref": ".codex/skills/read-and-acknowledge-messages/SKILL.md",
        },
        "ARCHIVED": {
            "stage_skill_ref": ".codex/skills/read-and-acknowledge-messages/SKILL.md",
        },
    }


def _legacy_message_workflow_graph() -> dict[str, object]:
    return {
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


def _legacy_message_stage_metadata() -> dict[str, object]:
    return {
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
