#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.company_paths import build_company_paths
from omniclaw.config import build_settings
from omniclaw.provisioning.scaffold import ensure_nanobot_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize or refresh a Nanobot config.json file.")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--config-path", default="")
    parser.add_argument("--seed-config", default="", help="Optional JSON file to merge into the baseline config")
    parser.add_argument("--primary-model", default="")
    parser.add_argument("--gateway-port", type=int, default=0)
    parser.add_argument("--company", default="")
    parser.add_argument("--global-config-path", default="")
    parser.add_argument("--company-workspace-root", default="")
    parser.add_argument("--apply", action="store_true", help="Write the config file (default: dry-run)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = build_settings(
        company=args.company or None,
        global_config_path=args.global_config_path or None,
        company_workspace_root=args.company_workspace_root or None,
    )
    company_paths = build_company_paths(settings)
    workspace_root = Path(args.workspace_root).expanduser().resolve()
    config_path = (
        Path(args.config_path).expanduser().resolve()
        if args.config_path
        else (workspace_root.parent / "config.json").resolve()
    )

    print(f"CONFIG path: {config_path}")
    print(f"WORKSPACE: {workspace_root}")
    if not args.apply:
        print("DRY-RUN mode. Use --apply to write the config.")
        return 0

    seed_config = Path(args.seed_config).expanduser().resolve() if args.seed_config else None
    if seed_config is not None and not seed_config.exists():
        raise SystemExit(f"seed config not found: {seed_config}")

    ensure_nanobot_config(
        config_path=config_path,
        workspace_root=workspace_root,
        apply=True,
        primary_model=args.primary_model or None,
        gateway_port=args.gateway_port or None,
        seed_config=None if seed_config is None else _load_seed_config(seed_config),
        template_root=company_paths.workspace_templates_root,
    )
    print("Config written.")
    return 0


def _load_seed_config(path: Path) -> dict[str, object]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())
