#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _nanobot_skill_common import load_json, render_nanobot_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize or refresh a Nanobot config.json file.")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--config-path", default="")
    parser.add_argument("--seed-config", default="", help="Optional JSON file to merge into the baseline config")
    parser.add_argument("--primary-model", default="")
    parser.add_argument("--gateway-port", type=int, default=0)
    parser.add_argument("--apply", action="store_true", help="Write the config file (default: dry-run)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_root = Path(args.workspace_root).expanduser().resolve()
    config_path = (
        Path(args.config_path).expanduser().resolve()
        if args.config_path
        else (workspace_root.parent / "config.json").resolve()
    )

    seed_payload: dict[str, object] | None = None
    if args.seed_config:
        seed_path = Path(args.seed_config).expanduser().resolve()
        if not seed_path.exists():
            raise SystemExit(f"seed config not found: {seed_path}")
        seed_payload = load_json(seed_path)

    merged = render_nanobot_config(
        config_path=config_path,
        workspace_root=workspace_root,
        primary_model=args.primary_model or None,
        gateway_port=args.gateway_port or None,
        seed_config=seed_payload,
    )

    print(f"CONFIG path: {config_path}")
    print(f"WORKSPACE: {workspace_root}")
    if not args.apply:
        print("DRY-RUN mode. Use --apply to write the config.")
        return 0

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    print("Config written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
