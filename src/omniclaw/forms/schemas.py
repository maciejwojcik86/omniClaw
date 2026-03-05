from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FormsActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "upsert_form_type",
        "validate_form_type",
        "activate_form_type",
        "deprecate_form_type",
        "delete_form_type",
        "list_form_types",
        "create_form",
        "transition_form",
        "acknowledge_message_read",
    ]

    type_key: str | None = None
    version: str | None = None
    lifecycle_state: str | None = None
    description: str | None = None
    workflow_graph: dict[str, Any] | None = None
    stage_metadata: dict[str, Any] | None = None

    form_id: str | None = None
    form_id_hint: str | None = None
    initial_status: str | None = None
    initial_holder_node_id: str | None = None

    actor_node_id: str | None = None
    actor_node_name: str | None = None
    decision_key: str | None = None
    to_status: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] | None = None
    set_fields: dict[str, Any] | None = None
