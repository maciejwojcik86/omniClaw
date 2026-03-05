#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.provisioning.scaffold import ensure_workspace_tree


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create OmniClaw workspace tree.")
    parser.add_argument("--workspace-root", required=True, help="Absolute or relative workspace root path")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply filesystem changes (default is dry-run)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root).expanduser().resolve()
    if not args.apply:
        print("DRY-RUN mode. Use --apply to write changes.")
        outcome = ensure_workspace_tree(workspace_root=root, apply=False)
    elif os.geteuid() == 0:
        outcome = ensure_workspace_tree(workspace_root=root, apply=True)
    else:
        try:
            outcome = ensure_workspace_tree(workspace_root=root, apply=True)
        except PermissionError:
            helper_path = os.getenv("OMNICLAW_PROVISIONING_HELPER_PATH", "").strip()
            helper_use_sudo = os.getenv("OMNICLAW_PROVISIONING_HELPER_USE_SUDO", "").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
            if not helper_path:
                raise SystemExit(
                    "Workspace apply failed due to permissions and no provisioning helper is configured. "
                    "Set OMNICLAW_PROVISIONING_HELPER_PATH or run as root."
                )
            if not os.access(helper_path, os.X_OK):
                raise SystemExit(f"Configured provisioning helper is not executable: {helper_path}")
            command = [helper_path, "create_workspace", str(root)]
            if helper_use_sudo:
                command = ["sudo", "-n", *command]
            subprocess.run(command, check=True)
            try:
                outcome = ensure_workspace_tree(workspace_root=root, apply=False)
            except PermissionError:
                outcome = {
                    "created_dirs": tuple(),
                    "existing_dirs": tuple(),
                    "created_files": tuple(),
                    "existing_files": tuple(),
                }
    for directory in outcome["created_dirs"]:
        print(f"CREATE dir  {directory}")
    for directory in outcome["existing_dirs"]:
        print(f"EXISTS dir  {directory}")
    for file_path in outcome["created_files"]:
        print(f"CREATE file {file_path}")
    for file_path in outcome["existing_files"]:
        print(f"EXISTS file {file_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
