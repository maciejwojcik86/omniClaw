#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.company_paths import build_company_paths
from omniclaw.config import build_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve OmniClaw company context from the global registry.")
    parser.add_argument("--company", help="Registered company slug or display name.")
    parser.add_argument("--global-config-path", help="Override OmniClaw global config path.")
    parser.add_argument("--company-workspace-root", help="Legacy explicit workspace root override.")
    parser.add_argument("--company-config-path", help="Legacy explicit company config path override.")
    parser.add_argument("--database-url", help="Explicit SQLAlchemy database URL override.")
    parser.add_argument("--field", help="Emit only one field value from the resolved context.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = build_settings(
        company=args.company,
        global_config_path=args.global_config_path,
        company_workspace_root=args.company_workspace_root,
        company_config_path=args.company_config_path,
        database_url=args.database_url,
    )
    company_paths = build_company_paths(settings)
    payload = {
        "global_config_path": settings.global_config_path,
        "company_slug": settings.company_slug,
        "company_display_name": settings.company_display_name,
        "workspace_root": str(company_paths.root),
        "database_file": str(company_paths.database_file),
        "agents_root": str(company_paths.agents_root),
        "forms_root": str(company_paths.forms_root),
        "master_skills_root": str(company_paths.master_skills_root),
        "instruction_templates_root": str(company_paths.instruction_templates_root),
        "workspace_templates_root": str(company_paths.workspace_templates_root),
        "form_archive_root": str(company_paths.form_archive_root),
        "logs_root": str(company_paths.logs_root),
        "activity_logs_root": str(company_paths.activity_logs_root),
        "retired_root": str(company_paths.retired_root),
        "retired_forms_root": str(company_paths.retired_forms_root),
        "retired_master_skills_root": str(company_paths.retired_master_skills_root),
        "runtime_packages_root": str(company_paths.runtime_packages_root),
        "finances_root": str(company_paths.finances_root),
    }
    if args.field:
        value = payload.get(args.field)
        if value is None:
            raise SystemExit(f"Unknown field: {args.field}")
        print(value)
        return 0

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
