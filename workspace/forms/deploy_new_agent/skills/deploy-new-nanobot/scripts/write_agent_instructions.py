#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _nanobot_skill_common import load_template_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write AGENTS.md in agent workspace root.")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--node-name", required=True)
    parser.add_argument("--role-name", default="Worker Agent")
    parser.add_argument("--manager-name", default="Human Supervisor")
    parser.add_argument("--source-file", default="", help="Optional markdown source file to use instead of template")
    parser.add_argument("--apply", action="store_true", help="Apply filesystem changes (default: dry-run)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root).expanduser().resolve()
    agents_path = root / "AGENTS.md"

    if args.source_file:
        content = Path(args.source_file).expanduser().resolve().read_text(encoding="utf-8")
    else:
        content = load_template_text("AGENTS.md").format(
            role_name=args.role_name,
            node_name=args.node_name,
            manager_name=args.manager_name,
        )

    if not args.apply:
        print("DRY-RUN mode. Use --apply to write AGENTS.md.")

    print(f"WRITE file {agents_path}")
    if args.apply:
        root.mkdir(parents=True, exist_ok=True)
        agents_path.write_text(content.rstrip() + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
