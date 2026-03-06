from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

REQUIRED_DIRS: tuple[str, ...] = (
    "inbox/unread",
    "inbox/read",
    "outbox/pending",
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
TEMPLATE_ROOT = REPO_ROOT / "workspace" / "agent_templates"

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


def _load_template_text(relative_path: str) -> str:
    return (TEMPLATE_ROOT / relative_path).read_text(encoding="utf-8")


def _load_template_json(relative_path: str) -> dict[str, object]:
    payload = json.loads((TEMPLATE_ROOT / relative_path).read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


REQUIRED_FILES: dict[str, str] = {
    relative_file: _load_template_text(template_relative)
    for relative_file, template_relative in REQUIRED_FILE_TEMPLATES.items()
}


NANOBOT_CONFIG_TEMPLATE: dict[str, object] = _load_template_json("config.json")


def ensure_workspace_tree(*, workspace_root: Path, apply: bool) -> dict[str, tuple[str, ...]]:
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
                target.write_text(_load_template_text(template_relative), encoding="utf-8")

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

    merged = deepcopy(NANOBOT_CONFIG_TEMPLATE)
    _deep_merge_dicts(merged, config_data)
    if seed_config:
        _deep_merge_dicts(merged, deepcopy(seed_config))

    defaults = merged.setdefault("agents", {}).setdefault("defaults", {})
    defaults["workspace"] = str(resolved_workspace)
    if primary_model:
        defaults["model"] = primary_model

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
