from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import HTTPException

from omniclaw.db.enums import NodeStatus, NodeType
from omniclaw.db.repository import KernelRepository
from omniclaw.provisioning.contracts import ProvisioningAdapter
from omniclaw.provisioning.schemas import ProvisioningActionRequest


class ProvisioningService:
    def __init__(self, *, adapter: ProvisioningAdapter, repository: KernelRepository):
        self._adapter = adapter
        self._repository = repository

    def execute(self, request: ProvisioningActionRequest) -> dict[str, object]:
        action = request.action

        if action == "create_linux_user":
            username = self._require(request.username, "username")
            home_dir = request.home_dir or f"/home/{username}"
            user_result = self._adapter.ensure_user(
                username=username,
                home_dir=home_dir,
                shell=request.shell,
                uid=request.uid,
                groups=request.groups,
            )

            response: dict[str, object] = {
                "action": action,
                "user": asdict(user_result),
            }

            if request.workspace and request.workspace.scaffold:
                workspace_result = self._adapter.ensure_workspace(
                    workspace_root=Path(request.workspace.root),
                )
                response["workspace"] = asdict(workspace_result)

            return self._attach_operations(response)

        if action == "create_workspace":
            workspace_root = self._resolve_workspace_root(request)
            workspace_result = self._adapter.ensure_workspace(workspace_root=workspace_root)
            return self._attach_operations(
                {
                    "action": action,
                    "workspace": asdict(workspace_result),
                }
            )

        if action == "apply_workspace_permissions":
            owner_user = request.owner_user or request.username
            manager_group = request.manager_group
            if not owner_user or not manager_group:
                raise HTTPException(status_code=422, detail="owner_user/username and manager_group are required")

            workspace_root = self._resolve_workspace_root(request)
            permission_result = self._adapter.apply_permissions(
                owner_user=owner_user,
                manager_group=manager_group,
                workspace_root=workspace_root,
            )
            return self._attach_operations(
                {
                    "action": action,
                    "permissions": asdict(permission_result),
                }
            )

        if action == "provision_agent":
            username = self._require(request.username, "username")
            home_dir = request.home_dir or f"/home/{username}"
            workspace_root = self._resolve_workspace_root(
                request,
                fallback=Path(home_dir) / "workspace",
            )
            user_result = self._adapter.ensure_user(
                username=username,
                home_dir=home_dir,
                shell=request.shell,
                uid=request.uid,
                groups=request.groups,
            )
            workspace_result = self._adapter.ensure_workspace(workspace_root=workspace_root)

            permission_result = None
            if request.manager_group:
                permission_result = self._adapter.apply_permissions(
                    owner_user=username,
                    manager_group=request.manager_group,
                    workspace_root=workspace_root,
                )

            resolved_name = request.node_name or username
            node, created = self._repository.upsert_node_by_name(
                node_type=NodeType.AGENT,
                name=resolved_name,
                status=NodeStatus.ACTIVE,
                linux_uid=user_result.uid,
                autonomy_level=request.autonomy_level,
            )

            if request.manager_node_id:
                self._repository.link_manager_if_missing(
                    parent_node_id=request.manager_node_id,
                    child_node_id=node.id,
                )

            result: dict[str, object] = {
                "action": action,
                "user": asdict(user_result),
                "workspace": asdict(workspace_result),
                "node": {
                    "id": node.id,
                    "type": node.type.value,
                    "name": node.name,
                    "linux_uid": node.linux_uid,
                    "status": node.status.value,
                    "autonomy_level": node.autonomy_level,
                    "created": created,
                },
            }
            if permission_result is not None:
                result["permissions"] = asdict(permission_result)
            return self._attach_operations(result)

        raise HTTPException(status_code=400, detail=f"Unsupported action '{action}'")

    def _resolve_workspace_root(
        self,
        request: ProvisioningActionRequest,
        *,
        fallback: Path | None = None,
    ) -> Path:
        if request.workspace is not None:
            return Path(request.workspace.root)
        if request.workspace_root:
            return Path(request.workspace_root)
        if fallback is not None:
            return fallback
        raise HTTPException(status_code=422, detail="workspace.root or workspace_root is required")

    def _require(self, value: str | None, field_name: str) -> str:
        if value:
            return value
        raise HTTPException(status_code=422, detail=f"{field_name} is required")

    def _attach_operations(self, result: dict[str, object]) -> dict[str, object]:
        if hasattr(self._adapter, "consume_operations"):
            operations = getattr(self._adapter, "consume_operations")()
            if operations:
                result["operations"] = operations
        return result
