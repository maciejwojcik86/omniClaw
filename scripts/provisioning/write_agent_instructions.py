#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_TEMPLATE = """# AGENTS.md

## Identity
- Role: {role_name}
- Node: {node_name}
- Manager: {manager_name}

## Mission
- Deliver tasks safely and deterministically.
- Draft formal MESSAGE replies in `outbox/drafts/` and submit by moving to `outbox/pending/`.
- Use `drafts/` for non-message artifacts only.

## Working Rules
- Read `inbox/unread` first, then active manager requests.
- Treat `SOUL.md`, `USER.md`, `TOOLS.md`, `memory/MEMORY.md`, and `memory/HISTORY.md` as durable context files.
- Follow `HEARTBEAT.md` exactly when a heartbeat cycle is requested.
- Update context files only when explicitly instructed by manager/kernel policy.
- Escalate blockers early with clear options.
- Do not change permissions, gateway bindings, or access controls directly.
- Keep execution inside this workspace and its `skills/` folder.

## Budget Awareness
- Prefer low-cost model strategy by default.
- If blocked by budget, prepare a budget request form.

## Completion Standard
- Output is reproducible and traceable.
- Keep manager-visible progress clear in deliverables and required context files.
- Leave `inbox/unread` empty after handling routed forms and archive outcomes through the workflow.
"""


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
        content = DEFAULT_TEMPLATE.format(
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
