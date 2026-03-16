from __future__ import annotations

import argparse
from pathlib import Path

from omniclaw.company_paths import build_company_paths
from omniclaw.config import build_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="List recent Nanobot prompt log artifacts for an agent.")
    parser.add_argument("--agent-name", required=True)
    parser.add_argument("--company")
    parser.add_argument("--global-config-path")
    parser.add_argument("--company-workspace-root")
    parser.add_argument("--limit", type=int, default=10)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = build_settings(
        company=args.company,
        global_config_path=args.global_config_path,
        company_workspace_root=args.company_workspace_root,
    )
    company_paths = build_company_paths(settings)
    prompt_logs_root = (
        company_paths.agents_root / args.agent_name / "workspace" / settings.runtime_output_boundary_rel / "prompt_logs"
    ).resolve()

    if not prompt_logs_root.exists():
        print(f"No prompt logs found at {prompt_logs_root}")
        return

    files = sorted(
        (path for path in prompt_logs_root.rglob("*.json") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in files[: max(args.limit, 1)]:
        print(path)


if __name__ == "__main__":
    main()
