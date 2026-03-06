#!/usr/bin/env python3
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.provisioning.scaffold import NANOBOT_CONFIG_TEMPLATE, _deep_merge_dicts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize or refresh a Nanobot config.json file.")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--config-path", default="")
    parser.add_argument("--seed-config", default="", help="Optional JSON file to merge into the baseline config")
    parser.add_argument("--primary-model", default="")
    parser.add_argument("--gateway-port", type=int, default=0)
    parser.add_argument("--apply", action="store_true", help="Write the config file (default: dry-run)")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    args = parse_args()
    workspace_root = Path(args.workspace_root).expanduser().resolve()
    config_path = (
        Path(args.config_path).expanduser().resolve()
        if args.config_path
        else (workspace_root.parent / "config.json").resolve()
    )

    merged = deepcopy(NANOBOT_CONFIG_TEMPLATE)
    _deep_merge_dicts(merged, load_json(config_path))

    if args.seed_config:
        seed_path = Path(args.seed_config).expanduser().resolve()
        if not seed_path.exists():
            raise SystemExit(f"seed config not found: {seed_path}")
        _deep_merge_dicts(merged, load_json(seed_path))

    defaults = merged.setdefault("agents", {}).setdefault("defaults", {})
    defaults["workspace"] = str(workspace_root)
    if args.primary_model:
        defaults["model"] = args.primary_model

    if args.gateway_port:
        merged.setdefault("gateway", {})["port"] = args.gateway_port

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
