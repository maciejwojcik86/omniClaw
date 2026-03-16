from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SkillsActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "list_master_skills",
        "list_active_master_skills",
        "draft_master_skill",
        "update_master_skill",
        "set_master_skill_status",
        "list_agent_skill_assignments",
        "assign_master_skills",
        "remove_master_skills",
        "sync_agent_skills",
    ]
    actor_node_id: str | None = None
    actor_node_name: str | None = None
    target_node_id: str | None = None
    target_node_name: str | None = None
    skill_name: str | None = None
    skill_names: list[str] = Field(default_factory=list)
    lifecycle_status: Literal["DRAFT", "ACTIVE", "DEACTIVATED"] | None = None
    source_path: str | None = None
    description: str | None = None
    version: str | None = None
    sync_scope: Literal["target", "all_active_agents"] = "target"
