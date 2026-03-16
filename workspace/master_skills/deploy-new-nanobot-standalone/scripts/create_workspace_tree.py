#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _nanobot_skill_common import ensure_workspace_tree


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
    try:
        outcome = ensure_workspace_tree(workspace_root=root, apply=args.apply)
    except PermissionError as exc:
        raise SystemExit(f"Workspace apply failed due to permissions: {exc}") from exc

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
