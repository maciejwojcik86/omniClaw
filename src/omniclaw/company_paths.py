from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from omniclaw.config import REPO_ROOT, Settings, resolve_company_workspace_root


REPO_WORKSPACE_ROOT = (REPO_ROOT / "workspace").resolve()


@dataclass(frozen=True)
class CompanyPaths:
    root: Path
    global_config_file: Path | None
    database_file: Path
    agents_root: Path
    forms_root: Path
    master_skills_root: Path
    instruction_templates_root: Path
    workspace_templates_root: Path
    form_archive_root: Path
    logs_root: Path
    activity_logs_root: Path
    retired_root: Path
    retired_forms_root: Path
    retired_master_skills_root: Path
    runtime_packages_root: Path
    finances_root: Path


def build_company_paths(settings: Settings) -> CompanyPaths:
    root = _infer_company_root(settings)
    return CompanyPaths(
        root=root,
        global_config_file=(
            Path(settings.global_config_path).expanduser().resolve() if settings.global_config_path else None
        ),
        database_file=(root / "omniclaw.db").resolve(),
        agents_root=(root / "agents").resolve(),
        forms_root=(root / "forms").resolve(),
        master_skills_root=(root / "master_skills").resolve(),
        instruction_templates_root=(root / "nanobots_instructions").resolve(),
        workspace_templates_root=(root / "nanobot_workspace_templates").resolve(),
        form_archive_root=(root / "form_archive").resolve(),
        logs_root=(root / "logs").resolve(),
        activity_logs_root=(root / "logs" / "activity").resolve(),
        retired_root=(root / "retired").resolve(),
        retired_forms_root=(root / "retired" / "forms").resolve(),
        retired_master_skills_root=(root / "retired" / "master_skills").resolve(),
        runtime_packages_root=(root / "runtime_packages").resolve(),
        finances_root=(root / "finances").resolve(),
    )


def repo_workspace_root() -> Path:
    return REPO_WORKSPACE_ROOT


def _infer_company_root(settings: Settings) -> Path:
    if settings.company_workspace_root:
        return resolve_company_workspace_root(settings.company_workspace_root)
    if settings.company_config_path:
        return Path(settings.company_config_path).expanduser().resolve().parent
    sqlite_root = _company_root_from_database_url(settings.database_url)
    if sqlite_root is not None:
        return sqlite_root
    return resolve_company_workspace_root(None)


def _company_root_from_database_url(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite") or database_url.endswith(":memory:"):
        return None
    parsed = urlparse(database_url)
    raw_path = unquote(parsed.path or "")
    if not raw_path:
        return None
    sqlite_path = Path(raw_path if database_url.startswith("sqlite:////") else raw_path.lstrip("/"))
    return sqlite_path.resolve().parent if sqlite_path.name else None
