from __future__ import annotations

from pathlib import Path
import subprocess

from omniclaw.provisioning.contracts import (
    PermissionProvisioningResult,
    UserProvisioningResult,
    WorkspaceProvisioningResult,
)
from omniclaw.provisioning.scaffold import ensure_workspace_tree


class SystemProvisioningAdapter:
    def ensure_user(
        self,
        *,
        username: str,
        home_dir: str,
        shell: str,
        uid: int | None = None,
        groups: list[str] | None = None,
    ) -> UserProvisioningResult:
        existing_uid = self._lookup_uid(username)
        created = existing_uid is None

        if created:
            command: list[str] = ["useradd", "-m", "-U", "-d", home_dir, "-s", shell]
            if uid is not None:
                command.extend(["-u", str(uid)])
            command.append(username)
            self._run(command)
            existing_uid = self._lookup_uid(username)

        if groups:
            group_csv = ",".join(groups)
            self._run(["usermod", "-aG", group_csv, username])

        return UserProvisioningResult(
            username=username,
            uid=existing_uid,
            home_dir=home_dir,
            shell=shell,
            created=created,
        )

    def ensure_workspace(self, *, workspace_root: Path) -> WorkspaceProvisioningResult:
        scaffold_result = ensure_workspace_tree(workspace_root=workspace_root, apply=True)
        return WorkspaceProvisioningResult(
            workspace_root=str(workspace_root.expanduser().resolve()),
            created_dirs=scaffold_result["created_dirs"],
            existing_dirs=scaffold_result["existing_dirs"],
            created_files=scaffold_result["created_files"],
            existing_files=scaffold_result["existing_files"],
        )

    def apply_permissions(
        self,
        *,
        owner_user: str,
        manager_group: str,
        workspace_root: Path,
    ) -> PermissionProvisioningResult:
        root = str(workspace_root.expanduser().resolve())
        self._run(["chown", "-R", f"{owner_user}:{manager_group}", root])
        self._run(["chmod", "-R", "u=rwX,g=rwX,o=", root])
        self._run(["find", root, "-type", "d", "-exec", "chmod", "g+s", "{}", "+"])
        return PermissionProvisioningResult(
            owner_user=owner_user,
            manager_group=manager_group,
            workspace_root=root,
            applied=True,
        )

    def _lookup_uid(self, username: str) -> int | None:
        process = subprocess.run(
            ["id", "-u", username],
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode != 0:
            return None
        return int(process.stdout.strip())

    def _run(self, command: list[str]) -> None:
        subprocess.run(command, capture_output=True, text=True, check=True)
