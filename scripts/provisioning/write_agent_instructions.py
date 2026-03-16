#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.company_paths import CompanyPaths, build_company_paths
from omniclaw.config import build_settings


PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}")
SUPPORTED_PLACEHOLDERS = {
    "node.name",
    "node.role_name",
    "node.primary_model",
    "current_time_utc",
    "manager.name",
    "manager.id",
    "line_manager",
    "subordinates_list",
    "inbox_unread_summary",
    "budget.mode",
    "budget.daily_inflow_usd",
    "budget.rollover_reserve_usd",
    "budget.remaining_usd",
    "budget.review_required_notice",
    "budget.direct_team_summary",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write external AGENTS template and rendered workspace AGENTS.md.")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--node-name", required=True)
    parser.add_argument("--role-name", default="Worker Agent")
    parser.add_argument("--manager-name", default="Human Supervisor")
    parser.add_argument("--primary-model", default="unassigned")
    parser.add_argument("--source-file", default="", help="Optional markdown source file to use instead of template")
    parser.add_argument("--company", default="")
    parser.add_argument("--global-config-path", default="")
    parser.add_argument("--company-workspace-root", default="")
    parser.add_argument("--apply", action="store_true", help="Apply filesystem changes (default: dry-run)")
    return parser.parse_args()


def derive_instruction_template_root(*, company_paths: CompanyPaths, node_name: str) -> Path:
    return company_paths.instruction_templates_root / node_name


def load_default_template(company_paths: CompanyPaths) -> str:
    template_path = company_paths.workspace_templates_root / "AGENTS.md"
    return template_path.read_text(encoding="utf-8")


def render_template(*, template_content: str, node_name: str, role_name: str, manager_name: str, primary_model: str) -> str:
    placeholders = {match.group(1).strip() for match in PLACEHOLDER_PATTERN.finditer(template_content)}
    unknown = sorted(placeholders - SUPPORTED_PLACEHOLDERS)
    if unknown:
        raise ValueError(f"unsupported placeholders: {', '.join(unknown)}")

    context = {
        "node.name": node_name,
        "node.role_name": role_name,
        "node.primary_model": primary_model or "unassigned",
        "current_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manager.name": manager_name,
        "manager.id": "",
        "line_manager": manager_name,
        "subordinates_list": "No direct subordinates.",
        "inbox_unread_summary": "No unread forms.",
        "budget.mode": "metered",
        "budget.daily_inflow_usd": "0.00",
        "budget.rollover_reserve_usd": "0.00",
        "budget.remaining_usd": "remaining $0.00",
        "budget.review_required_notice": "No budget review required.",
        "budget.direct_team_summary": "No direct team budget allocations.",
    }
    rendered = PLACEHOLDER_PATTERN.sub(lambda match: str(context[match.group(1).strip()]), template_content)
    return rendered.rstrip() + "\n"


def main() -> int:
    args = parse_args()
    settings = build_settings(
        company=args.company or None,
        global_config_path=args.global_config_path or None,
        company_workspace_root=args.company_workspace_root or None,
    )
    company_paths = build_company_paths(settings)
    workspace_root = Path(args.workspace_root).expanduser().resolve()
    agents_path = workspace_root / "AGENTS.md"

    template_root = derive_instruction_template_root(
        company_paths=company_paths,
        node_name=args.node_name,
    )
    template_path = template_root / "AGENTS.md"

    if args.source_file:
        template_content = Path(args.source_file).expanduser().resolve().read_text(encoding="utf-8")
    else:
        template_content = load_default_template(company_paths)

    rendered_content = render_template(
        template_content=template_content,
        node_name=args.node_name,
        role_name=args.role_name,
        manager_name=args.manager_name,
        primary_model=args.primary_model,
    )

    if not args.apply:
        print("DRY-RUN mode. Use --apply to write instructions.")

    print(f"WRITE template {template_path}")
    print(f"WRITE file {agents_path}")
    if args.apply:
        template_root.mkdir(parents=True, exist_ok=True)
        template_path.write_text(template_content.rstrip() + "\n", encoding="utf-8")
        workspace_root.mkdir(parents=True, exist_ok=True)
        agents_path.write_text(rendered_content, encoding="utf-8")
        agents_path.chmod(0o444)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
