from __future__ import annotations

import json
from pathlib import Path


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

REQUIRED_TEMPLATE_FILES: dict[str, str] = {
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


def find_repo_root(start: Path) -> Path | None:
    current = start.resolve()
    while True:
        if (current / "pyproject.toml").exists() and (current / "workspace").exists():
            return current
        if current == current.parent:
            return None
        current = current.parent


def template_root() -> Path:
    repo_root = find_repo_root(Path(__file__).resolve().parent)
    if repo_root is None:
        raise FileNotFoundError("Unable to locate OmniClaw repo root for workspace/nanobot_workspace_templates")
    root = repo_root / "workspace" / "nanobot_workspace_templates"
    if not root.exists():
        raise FileNotFoundError(f"Nanobot workspace template root not found: {root}")
    return root


def load_template_text(relative_path: str) -> str:
    path = template_root() / relative_path
    return path.read_text(encoding="utf-8")


def load_template_json(relative_path: str) -> dict[str, object]:
    path = template_root() / relative_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


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

    for relative_file, template_relative in REQUIRED_TEMPLATE_FILES.items():
        target = root / relative_file
        if target.exists():
            existing_files.append(str(target))
        else:
            created_files.append(str(target))
            if apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(load_template_text(template_relative), encoding="utf-8")

    return {
        "created_dirs": tuple(created_dirs),
        "existing_dirs": tuple(existing_dirs),
        "created_files": tuple(created_files),
        "existing_files": tuple(existing_files),
    }


def load_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def deep_merge_dicts(target: dict[str, object], source: dict[str, object]) -> None:
    for key, value in source.items():
        existing = target.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            deep_merge_dicts(existing, value)
        else:
            target[key] = value


def render_nanobot_config(
    *,
    config_path: Path,
    workspace_root: Path,
    primary_model: str | None = None,
    gateway_port: int | None = None,
    seed_config: dict[str, object] | None = None,
) -> dict[str, object]:
    merged = load_template_json("config.json")
    deep_merge_dicts(merged, load_json(config_path))
    if seed_config:
        deep_merge_dicts(merged, seed_config)

    defaults = merged.setdefault("agents", {}).setdefault("defaults", {})
    defaults["workspace"] = str(workspace_root.expanduser().resolve())
    if primary_model:
        defaults["model"] = primary_model

    if gateway_port:
        merged.setdefault("gateway", {})["port"] = gateway_port

    return merged
