#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from fastapi import HTTPException


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from omniclaw.company_paths import build_company_paths
from omniclaw.config import build_settings
from omniclaw.db.repository import KernelRepository
from omniclaw.db.models import FormLedger
from omniclaw.db.session import create_session_factory
from omniclaw.forms.schemas import FormsActionRequest
from omniclaw.forms.service import FormsService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync form_types table from workspace/forms/*/workflow.json definitions."
    )
    parser.add_argument(
        "--company",
        default="",
        help="Registered company slug or display name.",
    )
    parser.add_argument(
        "--global-config-path",
        default="",
        help="Override the OmniClaw global config path.",
    )
    parser.add_argument(
        "--company-workspace-root",
        default="",
        help="Legacy explicit company workspace root override.",
    )
    parser.add_argument(
        "--database-url",
        default="",
        help="SQLAlchemy database URL (default: sqlite under the selected company workspace)",
    )
    parser.add_argument(
        "--forms-root",
        default="",
        help="Forms root directory (default: <company-workspace-root>/forms)",
    )
    parser.add_argument(
        "--prune-missing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Delete DB form type versions not present under forms root "
            "(default: true, use --no-prune-missing to keep extras)"
        ),
    )
    return parser.parse_args()


def _load_workflow_payload(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"workflow file must contain a JSON object: {path}")
    return raw


def _sync_workflow(
    *,
    forms_service: FormsService,
    workflow_path: Path,
) -> tuple[str, str]:
    workflow = _load_workflow_payload(workflow_path)
    type_key = str(workflow.get("form_type") or workflow_path.parent.name).strip()
    version = str(workflow.get("version") or "1.0.0").strip()
    if not type_key:
        raise ValueError(f"missing form_type in {workflow_path}")
    if not version:
        raise ValueError(f"missing version in {workflow_path}")

    normalized_workflow = dict(workflow)
    normalized_workflow["form_type"] = type_key
    normalized_workflow["version"] = version

    description_raw = normalized_workflow.get("description")
    description = description_raw.strip() if isinstance(description_raw, str) else None
    stage_metadata = normalized_workflow.get("stage_metadata")
    if not isinstance(stage_metadata, dict):
        stage_metadata = {}

    forms_service.execute(
        FormsActionRequest(
            action="upsert_form_type",
            type_key=type_key,
            version=version,
            description=description,
            workflow_graph=normalized_workflow,
            stage_metadata=stage_metadata,
        )
    )
    validate = forms_service.execute(
        FormsActionRequest(
            action="validate_form_type",
            type_key=type_key,
            version=version,
        )
    )
    if not bool(validate.get("valid")):
        errors = validate.get("errors")
        raise ValueError(f"validation failed for {type_key}@{version}: {errors}")
    forms_service.execute(
        FormsActionRequest(
            action="activate_form_type",
            type_key=type_key,
            version=version,
        )
    )
    return type_key, version


def main() -> int:
    args = parse_args()
    settings = build_settings(
        company=args.company or None,
        global_config_path=args.global_config_path or None,
        company_workspace_root=args.company_workspace_root or None,
        database_url=args.database_url or None,
    )
    company_paths = build_company_paths(settings)
    forms_root = Path(args.forms_root or str(company_paths.forms_root)).resolve()
    if not forms_root.exists():
        print(f"forms root not found: {forms_root}", file=sys.stderr)
        return 1

    workflow_paths = sorted(forms_root.glob("*/workflow.json"))
    if not workflow_paths:
        print(f"no workflow.json files found under: {forms_root}", file=sys.stderr)
        return 1

    repository = KernelRepository(create_session_factory(settings.database_url), settings=settings)
    forms_service = FormsService(repository=repository, settings=settings)

    synced: set[tuple[str, str]] = set()
    print(f"syncing {len(workflow_paths)} workflow(s) from {forms_root}")
    for workflow_path in workflow_paths:
        try:
            type_key, version = _sync_workflow(forms_service=forms_service, workflow_path=workflow_path)
        except (ValueError, HTTPException) as exc:
            print(f"FAILED {workflow_path}: {exc}", file=sys.stderr)
            return 1
        synced.add((type_key, version))
        print(f"synced: {type_key}@{version} ({workflow_path})")

    removed: list[str] = []
    preserved: list[str] = []
    if args.prune_missing:
        session_factory = create_session_factory(settings.database_url)
        existing = repository.list_form_type_definitions()
        for definition in existing:
            key = (definition.type_key, definition.version)
            if key in synced:
                continue
            with session_factory() as session:
                ref_count = (
                    session.query(FormLedger)
                    .filter(
                        FormLedger.form_type_key == definition.type_key,
                        FormLedger.form_type_version == definition.version,
                    )
                    .count()
                )
            if ref_count > 0:
                preserved.append(f"{definition.type_key}@{definition.version} (referenced_by_forms={ref_count})")
                continue
            repository.delete_form_type_definition(type_key=definition.type_key, version=definition.version)
            removed.append(f"{definition.type_key}@{definition.version}")
        if removed:
            removed.sort()
            print("removed stale definitions:")
            for item in removed:
                print(f"- {item}")
        if preserved:
            preserved.sort()
            print("preserved stale definitions still referenced by forms_ledger:")
            for item in preserved:
                print(f"- {item}")

    print(f"done: synced={len(synced)} removed={len(removed)} preserved={len(preserved)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
