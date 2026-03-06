from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from fastapi import HTTPException

from omniclaw.db.enums import NodeStatus, NodeType
from omniclaw.db.models import Node
from omniclaw.db.repository import KernelRepository
from omniclaw.provisioning.contracts import ProvisioningAdapter
from omniclaw.provisioning.scaffold import ensure_nanobot_config
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

        if action == "register_human":
            username = self._require(request.username, "username")
            home_dir = request.home_dir or f"/home/{username}"
            workspace_root = self._resolve_workspace_root(
                request,
                fallback=self._default_human_workspace_root(username),
            )
            resolved_workspace_root = workspace_root.expanduser().resolve()
            runtime_config_path = self._resolve_config_path(
                request,
                home_dir=home_dir,
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

            primary_model = self._resolve_primary_model(
                request=request,
                runtime_config_path=runtime_config_path,
            )
            linux_password = self._resolve_linux_password(request)
            resolved_name = request.node_name or username

            node, created = self._repository.upsert_node_by_name(
                node_type=NodeType.HUMAN,
                name=resolved_name,
                status=NodeStatus.ACTIVE,
                linux_uid=user_result.uid,
                linux_username=username,
                linux_password=linux_password,
                workspace_root=str(resolved_workspace_root),
                runtime_config_path=str(runtime_config_path),
                primary_model=primary_model,
                autonomy_level=request.autonomy_level,
            )

            subordinate_count = len(self._repository.list_children(parent_node_id=node.id))
            result: dict[str, object] = {
                "action": action,
                "user": asdict(user_result),
                "workspace": asdict(workspace_result),
                "node": self._serialize_node(node=node, created=created),
                "line_management": {
                    "subordinate_count": subordinate_count,
                    "has_subordinate": subordinate_count > 0,
                },
            }
            if permission_result is not None:
                result["permissions"] = asdict(permission_result)
            return self._attach_operations(result)

        if action == "provision_agent":
            manager = self._resolve_manager_node(request=request, required=True)
            if manager is None:
                raise HTTPException(status_code=422, detail="manager_node_id or manager_node_name is required")

            resolved_name = request.node_name or request.username
            if not resolved_name:
                raise HTTPException(status_code=422, detail="node_name or username is required")

            username = request.username
            workspace_root = self._resolve_workspace_root(
                request,
                fallback=self._default_agent_workspace_root(resolved_name),
            )
            resolved_workspace_root = workspace_root.expanduser().resolve()
            runtime_config_path = self._resolve_config_path(
                request,
                workspace_root=resolved_workspace_root,
            )
            workspace_result = self._adapter.ensure_workspace(workspace_root=workspace_root)
            runtime_config_result = ensure_nanobot_config(
                config_path=runtime_config_path,
                workspace_root=resolved_workspace_root,
                apply=True,
                primary_model=request.primary_model,
            )
            primary_model = self._resolve_primary_model(
                request=request,
                runtime_config_path=runtime_config_path,
            )
            linux_password = self._resolve_linux_password(request)
            node, created = self._repository.upsert_node_by_name(
                node_type=NodeType.AGENT,
                name=resolved_name,
                status=NodeStatus.ACTIVE,
                linux_username=username,
                linux_password=linux_password,
                workspace_root=str(resolved_workspace_root),
                runtime_config_path=str(runtime_config_path),
                primary_model=primary_model,
                autonomy_level=request.autonomy_level,
            )

            try:
                self._repository.link_manager_if_missing(
                    parent_node_id=manager.id,
                    child_node_id=node.id,
                )
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc

            manager_subordinate_count = len(self._repository.list_children(parent_node_id=manager.id))
            result = {
                "action": action,
                "workspace": asdict(workspace_result),
                "runtime_config": runtime_config_result,
                "node": self._serialize_node(node=node, created=created),
                "manager": {
                    "id": manager.id,
                    "name": manager.name,
                    "type": manager.type.value,
                    "subordinate_count": manager_subordinate_count,
                },
            }
            return self._attach_operations(result)

        if action == "set_line_manager":
            manager = self._resolve_manager_node(request=request, required=True)
            if manager is None:
                raise HTTPException(status_code=422, detail="manager_node_id or manager_node_name is required")

            target = self._resolve_target_agent_node(request)
            try:
                relationship = self._repository.link_manager_if_missing(
                    parent_node_id=manager.id,
                    child_node_id=target.id,
                )
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc

            manager_subordinate_count = len(self._repository.list_children(parent_node_id=manager.id))
            return self._attach_operations(
                {
                    "action": action,
                    "manager": {
                        "id": manager.id,
                        "name": manager.name,
                        "type": manager.type.value,
                        "subordinate_count": manager_subordinate_count,
                    },
                    "target": {
                        "id": target.id,
                        "name": target.name,
                        "type": target.type.value,
                    },
                    "relationship": {
                        "id": relationship.id,
                        "parent_node_id": relationship.parent_node_id,
                        "child_node_id": relationship.child_node_id,
                        "relationship_type": relationship.relationship_type.value,
                    },
                }
            )

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

    def _resolve_config_path(
        self,
        request: ProvisioningActionRequest,
        *,
        home_dir: str | None = None,
        workspace_root: Path | None = None,
    ) -> Path:
        if request.runtime_config_path:
            return Path(request.runtime_config_path).expanduser().resolve()
        if workspace_root is not None:
            return (workspace_root.expanduser().resolve().parent / "config.json").resolve()
        if home_dir is None:
            raise HTTPException(status_code=422, detail="runtime_config_path could not be resolved")
        return (Path(home_dir) / ".nanobot" / "config.json").expanduser().resolve()

    def _default_human_workspace_root(self, username: str) -> Path:
        repo_root = Path(__file__).resolve().parents[3]
        return repo_root / "workspace" / username

    def _default_agent_workspace_root(self, agent_name: str) -> Path:
        repo_root = Path(__file__).resolve().parents[3]
        return repo_root / "workspace" / "agents" / agent_name / "workspace"

    def _resolve_manager_node(self, *, request: ProvisioningActionRequest, required: bool) -> Node | None:
        manager_node_id = request.manager_node_id
        manager_node_name = request.manager_node_name

        if not manager_node_id and not manager_node_name:
            if required:
                raise HTTPException(status_code=422, detail="manager_node_id or manager_node_name is required")
            return None

        manager = self._repository.get_node(node_id=manager_node_id, node_name=manager_node_name)
        if manager is None:
            raise HTTPException(status_code=422, detail="manager node not found")
        if manager.type not in {NodeType.HUMAN, NodeType.AGENT}:
            raise HTTPException(status_code=422, detail="manager node must be HUMAN or AGENT")
        return manager

    def _resolve_target_agent_node(self, request: ProvisioningActionRequest) -> Node:
        target_node_id = request.target_node_id
        target_node_name = request.target_node_name or request.node_name
        if not target_node_id and not target_node_name:
            raise HTTPException(status_code=422, detail="target_node_id or target_node_name/node_name is required")

        target = self._repository.get_node(
            node_id=target_node_id,
            node_name=target_node_name,
            node_type=NodeType.AGENT,
        )
        if target is None:
            raise HTTPException(status_code=404, detail="target agent node not found")
        return target

    def _resolve_primary_model(self, *, request: ProvisioningActionRequest, runtime_config_path: Path) -> str | None:
        if request.primary_model:
            return request.primary_model

        try:
            config = json.loads(runtime_config_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, PermissionError, OSError, json.JSONDecodeError):
            return None

        default_model = config.get("agents", {}).get("defaults", {}).get("model")
        if isinstance(default_model, str) and default_model.strip():
            return default_model.strip()

        nested_default_model = (
            config.get("agents", {})
            .get("defaults", {})
            .get("model", {})
            .get("primary")
        )
        if isinstance(nested_default_model, str) and nested_default_model.strip():
            return nested_default_model.strip()

        legacy_default_model = config.get("default_model")
        if isinstance(legacy_default_model, str) and legacy_default_model.strip():
            return legacy_default_model.strip()
        return None

    def _resolve_linux_password(self, request: ProvisioningActionRequest) -> str | None:
        if request.linux_password:
            return request.linux_password
        return None

    def _serialize_node(self, *, node: Node, created: bool) -> dict[str, object]:
        return {
            "id": node.id,
            "type": node.type.value,
            "name": node.name,
            "linux_uid": node.linux_uid,
            "linux_username": node.linux_username,
            "workspace_root": node.workspace_root,
            "runtime_config_path": node.runtime_config_path,
            "primary_model": node.primary_model,
            "password_present": bool(node.linux_password),
            "status": node.status.value,
            "autonomy_level": node.autonomy_level,
            "created": created,
        }

    def _attach_operations(self, result: dict[str, object]) -> dict[str, object]:
        if hasattr(self._adapter, "consume_operations"):
            operations = getattr(self._adapter, "consume_operations")()
            if operations:
                result["operations"] = operations
        return result
