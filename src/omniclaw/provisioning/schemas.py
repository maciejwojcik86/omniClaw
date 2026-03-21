from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceRequest(BaseModel):
    root: str
    scaffold: bool = True


class ProvisioningActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "create_linux_user",
        "create_workspace",
        "apply_workspace_permissions",
        "provision_agent",
        "register_human",
        "set_line_manager",
    ]
    username: str | None = None
    node_name: str | None = None
    home_dir: str | None = None
    shell: str = "/usr/sbin/nologin"
    uid: int | None = None
    groups: list[str] = Field(default_factory=list)
    workspace: WorkspaceRequest | None = None
    workspace_root: str | None = None
    owner_user: str | None = None
    manager_group: str | None = None
    manager_node_id: str | None = None
    manager_node_name: str | None = None
    target_node_id: str | None = None
    target_node_name: str | None = None
    autonomy_level: int = 2
    runtime_config_path: str | None = Field(default=None)
    role_name: str | None = None
    primary_model: str | None = None
    linux_password: str | None = None
