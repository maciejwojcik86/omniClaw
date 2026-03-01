from __future__ import annotations

from pathlib import Path

from omniclaw.provisioning.contracts import (
    PermissionProvisioningResult,
    UserProvisioningResult,
    WorkspaceProvisioningResult,
)
from omniclaw.provisioning.scaffold import REQUIRED_DIRS, REQUIRED_FILES


class MockProvisioningAdapter:
    def __init__(self, seed_uid: int = 20000):
        self._next_uid = seed_uid
        self._users: dict[str, UserProvisioningResult] = {}
        self._workspaces: set[str] = set()
        self._operations: list[dict[str, object]] = []

    def consume_operations(self) -> list[dict[str, object]]:
        operations = list(self._operations)
        self._operations.clear()
        return operations

    def ensure_user(
        self,
        *,
        username: str,
        home_dir: str,
        shell: str,
        uid: int | None = None,
        groups: list[str] | None = None,
    ) -> UserProvisioningResult:
        existing = self._users.get(username)
        if existing is not None:
            self._operations.append({"step": "ensure_user", "username": username, "created": False})
            if groups:
                self._operations.append(
                    {"step": "ensure_user_groups", "username": username, "groups": list(groups)}
                )
            return UserProvisioningResult(
                username=existing.username,
                uid=existing.uid,
                home_dir=existing.home_dir,
                shell=existing.shell,
                created=False,
            )

        resolved_uid = uid if uid is not None else self._next_uid
        if uid is None:
            self._next_uid += 1

        created = UserProvisioningResult(
            username=username,
            uid=resolved_uid,
            home_dir=home_dir,
            shell=shell,
            created=True,
        )
        self._users[username] = created
        self._operations.append({"step": "ensure_user", "username": username, "created": True, "uid": resolved_uid})
        if groups:
            self._operations.append({"step": "ensure_user_groups", "username": username, "groups": list(groups)})
        return created

    def ensure_workspace(self, *, workspace_root: Path) -> WorkspaceProvisioningResult:
        root = str(workspace_root.expanduser().resolve())
        is_new = root not in self._workspaces
        self._workspaces.add(root)

        all_dirs = (root,) + tuple(f"{root}/{relative}" for relative in REQUIRED_DIRS)
        all_files = tuple(f"{root}/{relative}" for relative in REQUIRED_FILES)

        if is_new:
            created_dirs = all_dirs
            existing_dirs = tuple()
            created_files = all_files
            existing_files = tuple()
        else:
            created_dirs = tuple()
            existing_dirs = all_dirs
            created_files = tuple()
            existing_files = all_files

        self._operations.append(
            {
                "step": "ensure_workspace",
                "workspace_root": root,
                "created": is_new,
            }
        )

        return WorkspaceProvisioningResult(
            workspace_root=root,
            created_dirs=created_dirs,
            existing_dirs=existing_dirs,
            created_files=created_files,
            existing_files=existing_files,
        )

    def apply_permissions(
        self,
        *,
        owner_user: str,
        manager_group: str,
        workspace_root: Path,
    ) -> PermissionProvisioningResult:
        resolved_root = str(workspace_root.expanduser().resolve())
        self._operations.append(
            {
                "step": "apply_permissions",
                "owner_user": owner_user,
                "manager_group": manager_group,
                "workspace_root": resolved_root,
            }
        )
        return PermissionProvisioningResult(
            owner_user=owner_user,
            manager_group=manager_group,
            workspace_root=resolved_root,
            applied=True,
        )
