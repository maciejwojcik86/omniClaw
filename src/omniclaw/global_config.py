from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

import yaml


_DEFAULT_ACCESS_SCOPE = "descendant"
_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class CompanyRegistryEntry:
    slug: str
    display_name: str
    workspace_root: str
    instructions: dict[str, Any]
    budgeting: dict[str, Any]
    hierarchy: dict[str, Any]
    skills: dict[str, Any]
    models: tuple[dict[str, Any], ...]
    runtime: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return {
            "display_name": self.display_name,
            "workspace_root": self.workspace_root,
            "instructions": dict(self.instructions),
            "budgeting": dict(self.budgeting),
            "hierarchy": dict(self.hierarchy),
            "skills": dict(self.skills),
            "models": [dict(item) for item in self.models],
            "runtime": dict(self.runtime),
        }


@dataclass(frozen=True)
class OmniClawGlobalConfig:
    path: Path
    schema_version: int
    companies: dict[str, CompanyRegistryEntry]

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "companies": {
                slug: entry.to_payload()
                for slug, entry in sorted(self.companies.items(), key=lambda item: item[0])
            },
        }


def default_global_config_path() -> Path:
    return (Path.home() / ".omniClaw" / "config.json").expanduser().resolve()


def resolve_global_config_path(raw_path: str | Path | None) -> Path:
    if raw_path is None:
        return default_global_config_path()
    return Path(raw_path).expanduser().resolve()


def load_global_config(
    raw_path: str | Path | None = None,
    *,
    allow_missing: bool = False,
) -> OmniClawGlobalConfig:
    path = resolve_global_config_path(raw_path)
    if not path.exists():
        if allow_missing:
            return OmniClawGlobalConfig(path=path, schema_version=1, companies={})
        raise FileNotFoundError(f"OmniClaw global config not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"OmniClaw global config must be a JSON object: {path}")

    raw_companies = payload.get("companies")
    if not isinstance(raw_companies, dict):
        raise ValueError(f"OmniClaw global config must contain an object property 'companies': {path}")

    companies: dict[str, CompanyRegistryEntry] = {}
    for slug, raw_entry in raw_companies.items():
        if not isinstance(raw_entry, dict):
            raise ValueError(f"Company entry '{slug}' must be a JSON object")
        companies[str(slug)] = _parse_company_entry(str(slug), raw_entry)

    schema_version = payload.get("schema_version", 1)
    try:
        resolved_schema_version = int(schema_version)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid schema_version in OmniClaw global config: {schema_version!r}") from exc

    return OmniClawGlobalConfig(path=path, schema_version=resolved_schema_version, companies=companies)


def write_global_config(config: OmniClawGlobalConfig) -> None:
    config.path.parent.mkdir(parents=True, exist_ok=True)
    config.path.write_text(json.dumps(config.to_payload(), indent=2) + "\n", encoding="utf-8")


def upsert_company_entry(
    *,
    raw_path: str | Path | None,
    company: CompanyRegistryEntry,
) -> OmniClawGlobalConfig:
    config = load_global_config(raw_path, allow_missing=True)
    companies = dict(config.companies)
    companies[company.slug] = company
    updated = OmniClawGlobalConfig(
        path=config.path,
        schema_version=max(config.schema_version, 1),
        companies=companies,
    )
    write_global_config(updated)
    return updated


def resolve_company_reference(
    config: OmniClawGlobalConfig,
    reference: str | None,
) -> CompanyRegistryEntry:
    if reference:
        direct = config.companies.get(reference)
        if direct is not None:
            return direct

        exact_display = [entry for entry in config.companies.values() if entry.display_name == reference]
        if len(exact_display) == 1:
            return exact_display[0]
        if len(exact_display) > 1:
            raise ValueError(
                f"Company display name '{reference}' is ambiguous; use one of the company slugs instead"
            )

        lower_reference = reference.casefold()
        ci_matches = [entry for entry in config.companies.values() if entry.display_name.casefold() == lower_reference]
        if len(ci_matches) == 1:
            return ci_matches[0]
        if len(ci_matches) > 1:
            raise ValueError(
                f"Company display name '{reference}' is ambiguous; use one of the company slugs instead"
            )
        raise ValueError(f"Company '{reference}' not found in OmniClaw global config")

    if len(config.companies) == 1:
        return next(iter(config.companies.values()))
    if not config.companies:
        raise ValueError("OmniClaw global config contains no registered companies")
    raise ValueError("Multiple companies are registered; pass --company <slug-or-display-name>")


def default_company_entry(*, slug: str, display_name: str, workspace_root: str | Path) -> CompanyRegistryEntry:
    return CompanyRegistryEntry(
        slug=slug,
        display_name=display_name,
        workspace_root=str(Path(workspace_root).expanduser().resolve()),
        instructions={"access_scope": _DEFAULT_ACCESS_SCOPE},
        budgeting={
            "daily_company_budget_usd": 0,
            "root_allocator_node": "UNSET_ROOT_ALLOCATOR",
            "reset_time_utc": "00:00",
        },
        hierarchy={
            "top_agent_node": "UNSET_TOP_AGENT",
        },
        skills={
            "default_agent_skill_names": ["form_workflow_authoring"],
        },
        models=(),
        runtime={
            "ipc_router_auto_scan_enabled": True,
            "ipc_router_scan_interval_seconds": 5,
            "budget_auto_cycle_enabled": True,
            "budget_auto_cycle_poll_interval_seconds": 60,
        },
    )


def build_company_entry(*, slug: str, payload: dict[str, Any]) -> CompanyRegistryEntry:
    return _parse_company_entry(slug, payload)


def slugify_company_slug(raw_value: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", raw_value.strip().casefold()).strip("-")
    if not normalized:
        raise ValueError("Company slug cannot be empty")
    return normalized


def load_legacy_model_catalog(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        return []
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return []
    raw_models = payload.get("models")
    if not isinstance(raw_models, list):
        return []
    return [dict(item) for item in raw_models if isinstance(item, dict)]


def _parse_company_entry(slug: str, payload: dict[str, Any]) -> CompanyRegistryEntry:
    display_name = str(payload.get("display_name") or slug).strip()
    raw_workspace_root = payload.get("workspace_root")
    if not raw_workspace_root or not str(raw_workspace_root).strip():
        raise ValueError(f"Company entry '{slug}' is missing workspace_root")

    instructions = _mapping(payload.get("instructions"))
    budgeting = _mapping(payload.get("budgeting"))
    hierarchy = _mapping(payload.get("hierarchy"))
    skills = _mapping(payload.get("skills"))
    runtime = _mapping(payload.get("runtime"))
    raw_models = payload.get("models", [])
    if raw_models is None:
        raw_models = []
    if not isinstance(raw_models, list):
        raise ValueError(f"Company entry '{slug}' has invalid models payload; expected a JSON array")
    models = tuple(_mapping(item) for item in raw_models)

    return CompanyRegistryEntry(
        slug=slug,
        display_name=display_name,
        workspace_root=str(Path(str(raw_workspace_root)).expanduser().resolve()),
        instructions=instructions or {"access_scope": _DEFAULT_ACCESS_SCOPE},
        budgeting=budgeting,
        hierarchy=hierarchy,
        skills=skills,
        models=models,
        runtime=runtime,
    )


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}
