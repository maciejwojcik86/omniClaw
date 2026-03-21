from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from omniclaw.company_paths import build_company_paths
from omniclaw.config import load_settings

REQUIRED_DIRS: tuple[str, ...] = (
    "inbox/new",
    "inbox/read",
    "outbox/send",
    "outbox/drafts",
    "outbox/archive",
    "outbox/dead-letter",
    "notes",
    "metrics",
    "drafts",
    "memory",
    "sessions",
    "skills",
)

REPO_ROOT = Path(__file__).resolve().parents[3]

REQUIRED_FILE_TEMPLATES: dict[str, str] = {
    "notes/DECISIONS.md": "notes/DECISIONS.md",
    "notes/BLOCKERS.md": "notes/BLOCKERS.md",
    "metrics/KPI.csv": "metrics/KPI.csv",
    "memory/MEMORY.md": "memory/MEMORY.md",
    "memory/HISTORY.md": "memory/HISTORY.md",
    "HEARTBEAT.md": "HEARTBEAT.md",
    "AGENTS.md": "AGENTS.placeholder.md",
    "SOUL.md": "SOUL.md",
    "USER.md": "USER.md",
    "TOOLS.md": "TOOLS.md",
}


def _resolve_template_root(template_root: Path | None) -> Path:
    if template_root is not None:
        resolved = template_root.expanduser().resolve()
        if resolved.exists():
            return resolved
        raise FileNotFoundError(f"explicit template_root does not exist: {resolved}")
    settings = load_settings()
    company_template_root = build_company_paths(settings).workspace_templates_root
    if not company_template_root.exists():
        raise FileNotFoundError(f"company workspace template root does not exist: {company_template_root}")
    return company_template_root


def _load_template_text(relative_path: str, *, template_root: Path | None = None) -> str:
    return (_resolve_template_root(template_root) / relative_path).read_text(encoding="utf-8")


def _load_template_json(relative_path: str, *, template_root: Path | None = None) -> dict[str, object]:
    payload = json.loads((_resolve_template_root(template_root) / relative_path).read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def ensure_workspace_tree(
    *,
    workspace_root: Path,
    apply: bool,
    template_root: Path | None = None,
) -> dict[str, tuple[str, ...]]:
    root = workspace_root.expanduser().resolve()

    created_dirs: list[str] = []
    existing_dirs: list[str] = []
    created_files: list[str] = []
    existing_files: list[str] = []

    if root.exists():
        existing_dirs.append(str(root))
    else:
        created_dirs.append(str(root))
        if apply:
            root.mkdir(parents=True, exist_ok=True)

    for relative_dir in REQUIRED_DIRS:
        target = root / relative_dir
        if target.exists():
            existing_dirs.append(str(target))
        else:
            created_dirs.append(str(target))
            if apply:
                target.mkdir(parents=True, exist_ok=True)

    for relative_file, template_relative in REQUIRED_FILE_TEMPLATES.items():
        target = root / relative_file
        if target.exists():
            existing_files.append(str(target))
        else:
            created_files.append(str(target))
            if apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    _load_template_text(template_relative, template_root=template_root),
                    encoding="utf-8",
                )

    return {
        "created_dirs": tuple(created_dirs),
        "existing_dirs": tuple(existing_dirs),
        "created_files": tuple(created_files),
        "existing_files": tuple(existing_files),
    }


def ensure_nanobot_config(
    *,
    config_path: Path,
    workspace_root: Path,
    apply: bool,
    primary_model: str | None = None,
    gateway_host: str | None = None,
    gateway_port: int | None = None,
    seed_config: dict[str, object] | None = None,
    litellm_api_base: str | None = None,
    litellm_api_key: str | None = None,
    template_root: Path | None = None,
) -> dict[str, object]:
    resolved_config = config_path.expanduser().resolve()
    resolved_workspace = workspace_root.expanduser().resolve()
    existed = resolved_config.exists()

    if existed:
        try:
            config_data = json.loads(resolved_config.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            config_data = {}
    else:
        config_data = {}

    merged = deepcopy(_load_template_json("config.json", template_root=template_root))
    _deep_merge_dicts(merged, config_data)
    if seed_config:
        _deep_merge_dicts(merged, deepcopy(seed_config))

    defaults = merged.setdefault("agents", {}).setdefault("defaults", {})
    defaults["workspace"] = str(resolved_workspace)
    if primary_model:
        defaults["model"] = primary_model
    if litellm_api_base or litellm_api_key:
        defaults["provider"] = "custom"
        provider_defaults = merged.setdefault("providers", {}).setdefault("custom", {})
        if litellm_api_base:
            provider_defaults["apiBase"] = litellm_api_base
        if litellm_api_key:
            provider_defaults["apiKey"] = litellm_api_key
    if litellm_api_base:
        defaults.pop("apiBase", None)
    if litellm_api_key:
        defaults.pop("apiKey", None)

    gateway = merged.setdefault("gateway", {})
    if gateway_host:
        gateway["host"] = gateway_host
    if gateway_port is not None:
        gateway["port"] = gateway_port

    created = not existed
    updated = existed
    if apply:
        resolved_config.parent.mkdir(parents=True, exist_ok=True)
        resolved_config.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")

    return {
        "path": str(resolved_config),
        "created": created,
        "updated": updated,
    }


def _deep_merge_dicts(target: dict[str, object], source: dict[str, object]) -> None:
    for key, value in source.items():
        existing = target.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            _deep_merge_dicts(existing, value)
        else:
            target[key] = value
