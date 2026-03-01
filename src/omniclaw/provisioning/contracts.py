from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class UserProvisioningResult:
    username: str
    uid: int | None
    home_dir: str
    shell: str
    created: bool


@dataclass(frozen=True)
class WorkspaceProvisioningResult:
    workspace_root: str
    created_dirs: tuple[str, ...]
    existing_dirs: tuple[str, ...]
    created_files: tuple[str, ...]
    existing_files: tuple[str, ...]


@dataclass(frozen=True)
class PermissionProvisioningResult:
    owner_user: str
    manager_group: str
    workspace_root: str
    applied: bool


class ProvisioningAdapter(Protocol):
    def ensure_user(
        self,
        *,
        username: str,
        home_dir: str,
        shell: str,
        uid: int | None = None,
        groups: list[str] | None = None,
    ) -> UserProvisioningResult:
        ...

    def ensure_workspace(self, *, workspace_root: Path) -> WorkspaceProvisioningResult:
        ...

    def apply_permissions(
        self,
        *,
        owner_user: str,
        manager_group: str,
        workspace_root: Path,
    ) -> PermissionProvisioningResult:
        ...
