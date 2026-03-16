#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
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


RESERVED_TOP_LEVEL = {
    "agents",
    "forms",
    "master_skills",
    "nanobots_instructions",
    "nanobot_workspace_templates",
    "form_archive",
    "logs",
    "retired",
    "runtime_packages",
    "finances",
}
TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".sh",
    ".py",
    ".csv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Copy a repo-local OmniClaw workspace into a registered company root.")
    parser.add_argument(
        "--company",
        default=os.getenv("OMNICLAW_COMPANY", "omniclaw"),
        help="Registered company slug or display name to update (default: omniclaw).",
    )
    parser.add_argument(
        "--display-name",
        default="",
        help="Display name stored in the global registry. Defaults to the existing value or a title-cased slug.",
    )
    parser.add_argument(
        "--global-config-path",
        default="",
        help="Override the OmniClaw global config path (default: ~/.omniClaw/config.json).",
    )
    parser.add_argument(
        "--source-workspace-root",
        default="",
        help="Source repo-local workspace root (default: <repo-root>/workspace).",
    )
    parser.add_argument(
        "--company-workspace-root",
        default="",
        help="Target company workspace root. Defaults to the existing registry entry or ~/.omniClaw/companies/<slug>.",
    )
    parser.add_argument(
        "--mode",
        choices=("copy", "move"),
        default="copy",
        help="Transfer mode (default: copy).",
    )
    parser.add_argument("--apply", action="store_true", help="Apply filesystem and registry changes (default: dry-run).")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow merging into an existing target workspace.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    slug = slugify_company_slug(args.company)
    source_root = Path(args.source_workspace_root).expanduser().resolve() if args.source_workspace_root else repo_workspace_root()
    registry = load_global_config(args.global_config_path or None, allow_missing=True)
    existing_entry = registry.companies.get(slug)
    target_root = _resolve_workspace_root(
        explicit_root=args.company_workspace_root,
        slug=slug,
        existing_entry=existing_entry,
    )
    settings = build_settings(
        company_workspace_root=str(target_root),
        global_config_path=args.global_config_path or None,
    )
    company_paths = build_company_paths(settings)
    display_name = args.display_name.strip() or (
        existing_entry.display_name if existing_entry is not None else slug.replace("-", " ").title()
    )

    if not source_root.exists():
        raise SystemExit(f"source workspace does not exist: {source_root}")
    if source_root == target_root:
        raise SystemExit("source and target company workspace roots are identical")
    if target_root.exists() and any(target_root.iterdir()) and not args.force and target_root != source_root:
        raise SystemExit("target company workspace already contains files; rerun with --force to merge into it")

    if args.apply:
        _ensure_target_roots(company_paths)

    transferred: list[str] = []
    preserved: list[str] = []
    rewritten_text_files: list[str] = []

    mapping = {
        source_root / "omniclaw.db": target_root / "omniclaw.db",
        source_root / "README.md": target_root / "README.md",
        source_root / "forms": company_paths.forms_root,
        source_root / "master_skills": company_paths.master_skills_root,
        source_root / "nanobots_instructions": company_paths.instruction_templates_root,
        source_root / "nanobot_workspace_templates": company_paths.workspace_templates_root,
        source_root / "agents": company_paths.agents_root,
        source_root / "form_archive": company_paths.form_archive_root,
        source_root / "logs": company_paths.logs_root,
        source_root / "retired": company_paths.retired_root,
        source_root / "runtime_packages": company_paths.runtime_packages_root,
        source_root / "finances": company_paths.finances_root,
    }

    for child in sorted(source_root.iterdir(), key=lambda item: item.name):
        if child in mapping or child.name in {"config.json", "company_config.json", "company_models.yaml", "models"}:
            continue
        if child.is_dir() and child.name not in RESERVED_TOP_LEVEL and not child.name.startswith("."):
            mapping[child] = target_root / child.name

    for source, target in mapping.items():
        if not source.exists():
            continue
        if _target_conflicts(target) and not args.force:
            preserved.append(str(target))
            continue
        transferred.append(f"{source} -> {target}")
        if args.apply:
            _transfer(source=source, target=target, mode=args.mode)

    entry = _build_registry_entry(
        slug=slug,
        display_name=display_name,
        workspace_root=target_root,
        existing_entry=existing_entry,
        source_root=source_root,
    )

    if args.apply:
        upsert_company_entry(raw_path=args.global_config_path or None, company=entry)
        rewritten_text_files = _rewrite_text_paths(
            target_root=target_root,
            source_root=source_root,
            global_config_path=registry.path,
        )
        database_updates = 0
        if company_paths.database_file.exists():
            database_updates = _rewrite_database_paths(
                db_path=company_paths.database_file,
                source_root=source_root,
                target_root=target_root,
                global_config_path=registry.path,
            )
        _remove_legacy_company_config_files(target_root)
        print("Migration applied.")
        print(f"DB rewrites: {database_updates}")
        print(f"Text rewrites: {len(rewritten_text_files)}")
    else:
        print("DRY-RUN migration. Use --apply to copy the repo-local workspace and register the company.")

    for item in transferred:
        print(f"TRANSFER   {item}")
    for item in preserved:
        print(f"PRESERVE   {item}")
    for item in rewritten_text_files:
        print(f"REWRITE    {item}")
    print(f"COMPANY    {entry.slug} ({entry.display_name})")
    print(f"SOURCE     {source_root}")
    print(f"TARGET     {target_root}")
    print(f"REGISTRY   {registry.path}")
    print(f"DATABASE   {company_paths.database_file}")
    return 0


def _build_registry_entry(
    *,
    slug: str,
    display_name: str,
    workspace_root: Path,
    existing_entry: CompanyRegistryEntry | None,
    source_root: Path,
) -> CompanyRegistryEntry:
    payload = (
        existing_entry.to_payload()
        if existing_entry is not None
        else default_company_entry(slug=slug, display_name=display_name, workspace_root=workspace_root).to_payload()
    )
    payload["display_name"] = display_name
    payload["workspace_root"] = str(workspace_root)

    legacy_config_path = _first_existing(source_root / "config.json", source_root / "company_config.json")
    if legacy_config_path is not None:
        legacy_payload = _load_json(legacy_config_path)
        for section_name in ("instructions", "budgeting", "hierarchy", "skills", "runtime"):
            section_value = legacy_payload.get(section_name)
            if isinstance(section_value, dict):
                payload[section_name] = section_value

    legacy_model_path = _first_existing(source_root / "models" / "company_models.yaml", source_root / "company_models.yaml")
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


def _ensure_target_roots(company_paths) -> None:
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
        directory.mkdir(parents=True, exist_ok=True)


def _transfer(*, source: Path, target: Path, mode: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if _target_conflicts(target):
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    if mode == "move":
        shutil.move(str(source), str(target))
        return
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        shutil.copy2(source, target)


def _target_conflicts(target: Path) -> bool:
    if not target.exists():
        return False
    if target.is_file():
        return True
    try:
        next(target.iterdir())
    except StopIteration:
        return False
    return True


def _rewrite_text_paths(
    *,
    target_root: Path,
    source_root: Path,
    global_config_path: Path,
) -> list[str]:
    rewritten: list[str] = []
    replacements = {
        str(source_root): str(target_root),
        str(source_root / "company_config.json"): str(global_config_path),
        str(source_root / "config.json"): str(global_config_path),
        str(source_root / "company_models.yaml"): str(global_config_path),
        str(source_root / "models" / "company_models.yaml"): str(global_config_path),
    }
    for path in sorted(target_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        updated = _rewrite_string(content, replacements)
        if updated == content:
            continue
        path.write_text(updated, encoding="utf-8")
        rewritten.append(str(path))
    return rewritten


def _rewrite_database_paths(
    *,
    db_path: Path,
    source_root: Path,
    target_root: Path,
    global_config_path: Path,
) -> int:
    replacements = {
        str(source_root): str(target_root),
        str(source_root / "company_config.json"): str(global_config_path),
        str(source_root / "config.json"): str(global_config_path),
        str(source_root / "company_models.yaml"): str(global_config_path),
        str(source_root / "models" / "company_models.yaml"): str(global_config_path),
    }
    updates = 0
    connection = sqlite3.connect(str(db_path))
    try:
        cursor = connection.cursor()
        updates += _rewrite_table_columns(
            cursor,
            "nodes",
            ("workspace_root", "runtime_config_path", "instruction_template_root"),
            replacements,
        )
        updates += _rewrite_table_columns(cursor, "master_skills", ("master_path",), replacements)
        updates += _rewrite_table_columns(
            cursor,
            "forms_ledger",
            ("source_path", "delivery_path", "archive_path", "dead_letter_path"),
            replacements,
        )
        updates += _rewrite_json_column(cursor, "forms_ledger", "history_log", replacements)
        updates += _rewrite_json_column(cursor, "form_transition_events", "payload_json", replacements)
        connection.commit()
    finally:
        connection.close()
    return updates


def _rewrite_table_columns(
    cursor: sqlite3.Cursor,
    table: str,
    columns: tuple[str, ...],
    replacements: dict[str, str],
) -> int:
    updates = 0
    for column in columns:
        rows = cursor.execute(f"SELECT rowid, {column} FROM {table} WHERE {column} IS NOT NULL").fetchall()
        for rowid, value in rows:
            if not isinstance(value, str):
                continue
            rewritten = _rewrite_string(value, replacements)
            if rewritten == value:
                continue
            cursor.execute(f"UPDATE {table} SET {column} = ? WHERE rowid = ?", (rewritten, rowid))
            updates += 1
    return updates


def _rewrite_json_column(
    cursor: sqlite3.Cursor,
    table: str,
    column: str,
    replacements: dict[str, str],
) -> int:
    updates = 0
    rows = cursor.execute(f"SELECT rowid, {column} FROM {table} WHERE {column} IS NOT NULL").fetchall()
    for rowid, raw in rows:
        if not isinstance(raw, str) or not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        rewritten = _rewrite_json_value(payload, replacements)
        if rewritten == payload:
            continue
        cursor.execute(
            f"UPDATE {table} SET {column} = ? WHERE rowid = ?",
            (json.dumps(rewritten, separators=(",", ":")), rowid),
        )
        updates += 1
    return updates


def _rewrite_json_value(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        return _rewrite_string(value, replacements)
    if isinstance(value, list):
        return [_rewrite_json_value(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _rewrite_json_value(item, replacements) for key, item in value.items()}
    return value


def _rewrite_string(value: str, replacements: dict[str, str]) -> str:
    rewritten = value
    for old, new in replacements.items():
        rewritten = rewritten.replace(old, new)
    return rewritten


def _remove_legacy_company_config_files(target_root: Path) -> None:
    for candidate in (
        target_root / "config.json",
        target_root / "company_config.json",
        target_root / "company_models.yaml",
        target_root / "models" / "company_models.yaml",
    ):
        if not candidate.exists():
            continue
        if candidate.is_file():
            candidate.unlink()
    models_root = target_root / "models"
    if models_root.exists() and models_root.is_dir():
        try:
            next(models_root.iterdir())
        except StopIteration:
            models_root.rmdir()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _first_existing(*candidates: Path) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


if __name__ == "__main__":
    raise SystemExit(main())
