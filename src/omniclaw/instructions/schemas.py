from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class InstructionsActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "list_accessible_targets",
        "get_template",
        "preview_render",
        "set_template",
        "sync_render",
    ]
    actor_node_id: str | None = None
    actor_node_name: str | None = None
    target_node_id: str | None = None
    target_node_name: str | None = None
    template_content: str | None = None
    sync_scope: Literal["target", "all_active_agents"] = "target"
