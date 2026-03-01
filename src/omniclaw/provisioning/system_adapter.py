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
    def __init__(
        self,
        *,
        helper_path: str | None = None,
        helper_use_sudo: bool = False,
    ) -> None:
        self._helper_path = str(Path(helper_path).expanduser().resolve()) if helper_path else None
        self._helper_use_sudo = helper_use_sudo

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
            if self._helper_path:
                helper_command = [
                    "create_user",
                    username,
                    home_dir,
                    shell,
                    str(uid) if uid is not None else "",
                ]
                self._run_helper(helper_command)
            else:
                command: list[str] = ["useradd", "-m", "-U", "-d", home_dir, "-s", shell]
                if uid is not None:
                    command.extend(["-u", str(uid)])
                command.append(username)
                self._run(command)
            existing_uid = self._lookup_uid(username)

        if groups:
            group_csv = ",".join(groups)
            if self._helper_path:
                self._run_helper(["add_groups", username, group_csv])
            else:
                self._run(["usermod", "-aG", group_csv, username])

        return UserProvisioningResult(
            username=username,
            uid=existing_uid,
            home_dir=home_dir,
            shell=shell,
            created=created,
        )

    def ensure_workspace(self, *, workspace_root: Path) -> WorkspaceProvisioningResult:
        root = workspace_root.expanduser().resolve()
        if self._helper_path:
            self._run_helper(["create_workspace", str(root)])
            # Kernel process may not have permission to traverse the newly-created
            # workspace home path; return best-effort preview metadata.
            try:
                scaffold_result = ensure_workspace_tree(workspace_root=root, apply=False)
            except PermissionError:
                scaffold_result = {
                    "created_dirs": tuple(),
                    "existing_dirs": tuple(),
                    "created_files": tuple(),
                    "existing_files": tuple(),
                }
        else:
            scaffold_result = ensure_workspace_tree(workspace_root=root, apply=True)
        return WorkspaceProvisioningResult(
            workspace_root=str(root),
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
        home_root = str(workspace_root.expanduser().resolve().parent)
        if self._helper_path:
            self._run_helper(["apply_permissions", owner_user, manager_group, root])
        else:
            self._run(["chown", f"{owner_user}:{manager_group}", home_root])
            self._run(["chmod", "u=rwx,g=rx,o=", home_root])
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
        command = ["id", "-u", username]
        if self._helper_path:
            command = self._build_helper_command(["id_uid", username])
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode != 0:
            return None
        return int(process.stdout.strip())

    def _run(self, command: list[str]) -> None:
        subprocess.run(command, capture_output=True, text=True, check=True)

    def _run_helper(self, command: list[str]) -> None:
        subprocess.run(self._build_helper_command(command), capture_output=True, text=True, check=True)

    def _build_helper_command(self, command: list[str]) -> list[str]:
        if not self._helper_path:
            raise RuntimeError("Helper path is not configured")
        if self._helper_use_sudo:
            return ["sudo", "-n", self._helper_path, *command]
        return [self._helper_path, *command]
