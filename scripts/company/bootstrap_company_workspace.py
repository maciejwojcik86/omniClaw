#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.company_paths import build_company_paths, repo_workspace_root
from omniclaw.config import build_settings, default_company_workspace_root
from omniclaw.global_config import (
    CompanyRegistryEntry,
    build_company_entry,
    default_company_entry,
    load_global_config,
    load_legacy_model_catalog,
    slugify_company_slug,
    upsert_company_entry,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold and register an OmniClaw company workspace.")
    parser.add_argument(
        "--company",
        default=os.getenv("OMNICLAW_COMPANY", "omniclaw"),
        help="Registered company slug or display name to create/update (default: omniclaw).",
    )
    parser.add_argument(
        "--display-name",
        default="",
        help="Display name stored in the global registry. Defaults to a title-cased version of the company slug.",
    )
    parser.add_argument(
        "--global-config-path",
        default="",
        help="Override the OmniClaw global config path (default: ~/.omniClaw/config.json).",
    )
    parser.add_argument(
        "--company-workspace-root",
        default="",
        help="Selected company workspace root. Defaults to the existing registry entry or ~/.omniClaw/companies/<slug>.",
    )
    parser.add_argument(
        "--seed-workspace-root",
        default="",
        help="Optional seed workspace root for baseline forms/skills/templates and legacy company settings.",
    )
    parser.add_argument("--apply", action="store_true", help="Apply filesystem and registry changes (default: dry-run).")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow copying baseline assets into existing targets when they are missing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    slug = slugify_company_slug(args.company)
    registry = load_global_config(args.global_config_path or None, allow_missing=True)
    existing_entry = registry.companies.get(slug)
    workspace_root = _resolve_workspace_root(
        explicit_root=args.company_workspace_root,
        slug=slug,
        existing_entry=existing_entry,
    )
    settings = build_settings(
        company_workspace_root=str(workspace_root),
        global_config_path=args.global_config_path or None,
    )
    company_paths = build_company_paths(settings)
    seed_root = Path(args.seed_workspace_root).expanduser().resolve() if args.seed_workspace_root else repo_workspace_root()
    display_name = args.display_name.strip() or (
        existing_entry.display_name if existing_entry is not None else slug.replace("-", " ").title()
    )

    created_dirs: list[str] = []
    existing_dirs: list[str] = []
    copied_items: list[str] = []
    skipped_items: list[str] = []

    for directory in (
        company_paths.root,
        company_paths.agents_root,
        company_paths.forms_root,
        company_paths.master_skills_root,
        company_paths.instruction_templates_root,
        company_paths.workspace_templates_root,
        company_paths.form_archive_root,
        company_paths.logs_root,
        company_paths.activity_logs_root,
        company_paths.retired_root,
        company_paths.retired_forms_root,
        company_paths.retired_master_skills_root,
        company_paths.runtime_packages_root,
        company_paths.finances_root,
    ):
        if directory.exists():
            existing_dirs.append(str(directory))
            continue
        created_dirs.append(str(directory))
        if args.apply:
            directory.mkdir(parents=True, exist_ok=True)

    seed_map = {
        seed_root / "forms": company_paths.forms_root,
        seed_root / "master_skills": company_paths.master_skills_root,
        seed_root / "nanobot_workspace_templates": company_paths.workspace_templates_root,
    }
    for source, target in seed_map.items():
        if not source.exists():
            skipped_items.append(f"missing seed directory: {source}")
            continue
        if target.exists() and any(target.iterdir()) and not args.force:
            skipped_items.append(f"existing target directory preserved: {target}")
            continue
        copied_items.append(f"{source} -> {target}")
        if args.apply:
            shutil.copytree(source, target, dirs_exist_ok=True)

    entry = _build_registry_entry(
        slug=slug,
        display_name=display_name,
        workspace_root=workspace_root,
        existing_entry=existing_entry,
        seed_root=seed_root,
    )
    if args.apply:
        upsert_company_entry(raw_path=args.global_config_path or None, company=entry)
        print("Bootstrap applied.")
    else:
        print("DRY-RUN bootstrap. Use --apply to create the company workspace and registry entry.")

    for item in created_dirs:
        print(f"CREATE dir  {item}")
    for item in existing_dirs:
        print(f"EXISTS dir  {item}")
    for item in copied_items:
        print(f"SEED       {item}")
    for item in skipped_items:
        print(f"SKIP       {item}")
    print(f"COMPANY    {entry.slug} ({entry.display_name})")
    print(f"WORKSPACE  {entry.workspace_root}")
    print(f"REGISTRY   {registry.path}")
    return 0


def _build_registry_entry(
    *,
    slug: str,
    display_name: str,
    workspace_root: Path,
    existing_entry: CompanyRegistryEntry | None,
    seed_root: Path,
) -> CompanyRegistryEntry:
    payload = (
        existing_entry.to_payload()
        if existing_entry is not None
        else default_company_entry(slug=slug, display_name=display_name, workspace_root=workspace_root).to_payload()
    )
    payload["display_name"] = display_name
    payload["workspace_root"] = str(workspace_root)

    legacy_config_path = _first_existing(seed_root / "config.json", seed_root / "company_config.json")
    if legacy_config_path is not None:
        legacy_payload = _load_json(legacy_config_path)
        for section_name in ("instructions", "budgeting", "hierarchy", "skills", "runtime"):
            section_value = legacy_payload.get(section_name)
            if isinstance(section_value, dict):
                payload[section_name] = section_value

    legacy_model_path = _first_existing(seed_root / "models" / "company_models.yaml", seed_root / "company_models.yaml")
    models = load_legacy_model_catalog(legacy_model_path)
    if models:
        payload["models"] = models

    return build_company_entry(slug=slug, payload=payload)


def _default_workspace_root_for_slug(slug: str) -> Path:
    if slug == "omniclaw":
        return default_company_workspace_root()
    return (Path.home() / ".omniClaw" / "companies" / slug).expanduser().resolve()


def _resolve_workspace_root(
    *,
    explicit_root: str,
    slug: str,
    existing_entry: CompanyRegistryEntry | None,
) -> Path:
    if explicit_root:
        return Path(explicit_root).expanduser().resolve()
    if existing_entry is not None:
        return Path(existing_entry.workspace_root).expanduser().resolve()
    return _default_workspace_root_for_slug(slug)


def _first_existing(*candidates: Path) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())
