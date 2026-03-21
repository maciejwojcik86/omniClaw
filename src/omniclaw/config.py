from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from omniclaw.global_config import (
    CompanyRegistryEntry,
    load_global_config,
    resolve_company_reference,
    resolve_global_config_path,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    log_level: str
    database_url: str
    provisioning_mode: str
    allow_privileged_provisioning: bool
    provisioning_helper_path: str | None = None
    provisioning_helper_use_sudo: bool = False
    runtime_mode: str = "mock"
    allow_privileged_runtime: bool = False
    runtime_use_sudo: bool = False
    runtime_command_bin: str = "nanobot"
    runtime_gateway_command_template: str = (
        "{runtime_bin} gateway --workspace {workspace_root} --config {config_path} --port {port}"
    )
    runtime_command_timeout_seconds: int = 30
    runtime_output_boundary_rel: str = "drafts/runtime"
    ipc_queue_paths: tuple[str, ...] = ("outbox/send", "outbox/pending")
    ipc_archive_rel: str = "outbox/archive"
    ipc_dead_letter_rel: str = "outbox/dead-letter"
    ipc_inbox_new_rel: str = "inbox/new"
    ipc_router_scan_interval_seconds: int = 5
    ipc_router_auto_scan_enabled: bool = True
    budget_auto_cycle_enabled: bool = True
    budget_auto_cycle_poll_interval_seconds: int = 60
    runtime_retry_scheduler_enabled: bool = True
    runtime_retry_scheduler_poll_interval_seconds: int = 60
    global_config_path: str | None = None
    company_slug: str | None = None
    company_display_name: str | None = None
    company_workspace_root: str | None = None
    company_config_path: str | None = None
    company_settings: Mapping[str, Any] | None = None
    litellm_proxy_url: str | None = None
    litellm_master_key: str | None = None
    litellm_auto_start_local_proxy: bool = True
    litellm_local_config_path: str | None = None
    litellm_startup_timeout_seconds: int = 30

    @property
    def ipc_inbox_unread_rel(self) -> str:
        return self.ipc_inbox_new_rel

    def company_section(self, name: str) -> dict[str, Any]:
        payload = self.company_settings or {}
        value = payload.get(name) if isinstance(payload, Mapping) else None
        return dict(value) if isinstance(value, Mapping) else {}


def _parse_bool(raw_value: str | None, default: bool) -> bool:
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_int(raw_value: str | None, default: int) -> int:
    if raw_value is None:
        return default
    try:
        return int(raw_value.strip())
    except ValueError:
        return default


def _parse_csv_paths(raw_value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if raw_value is None:
        return default
    values = tuple(part.strip().strip("/") for part in raw_value.split(",") if part.strip().strip("/"))
    if not values:
        return default
    return values


def default_company_workspace_root() -> Path:
    return (Path.home() / ".omniClaw" / "workspace").expanduser().resolve()


def resolve_company_workspace_root(raw_path: str | Path | None) -> Path:
    if raw_path is None:
        return default_company_workspace_root()
    return Path(raw_path).expanduser().resolve()


def resolve_company_config_path(
    *,
    workspace_root: Path,
    raw_path: str | Path | None,
) -> Path:
    if raw_path is not None:
        return Path(raw_path).expanduser().resolve()

    preferred = (workspace_root / "config.json").resolve()
    # Keep the old filename only for explicit compatibility/test flows that bypass
    # the global company registry. The canonical runtime path is `config.json`.
    legacy = (workspace_root / "company_config.json").resolve()
    if preferred.exists():
        return preferred
    if legacy.exists():
        return legacy
    return preferred


def resolve_database_url(*, workspace_root: Path, raw_database_url: str | None) -> str:
    if raw_database_url:
        return raw_database_url
    return f"sqlite:///{(workspace_root / 'omniclaw.db').resolve()}"


def _env_get(env: Mapping[str, str], key: str) -> str | None:
    return env.get(key)


def build_settings(
    *,
    env: Mapping[str, str] | None = None,
    company: str | None = None,
    global_config_path: str | Path | None = None,
    company_workspace_root: str | Path | None = None,
    company_config_path: str | Path | None = None,
    database_url: str | None = None,
) -> Settings:
    resolved_env = env or os.environ
    helper_path = _env_get(resolved_env, "OMNICLAW_PROVISIONING_HELPER_PATH")
    explicit_company = company if company is not None else _env_get(resolved_env, "OMNICLAW_COMPANY")
    explicit_workspace_root = (
        company_workspace_root
        if company_workspace_root is not None
        else _env_get(resolved_env, "OMNICLAW_COMPANY_WORKSPACE_ROOT")
    )
    explicit_company_config_path = (
        company_config_path
        if company_config_path is not None
        else _env_get(resolved_env, "OMNICLAW_COMPANY_CONFIG_PATH")
    )
    resolved_global_config_path = resolve_global_config_path(
        global_config_path if global_config_path is not None else _env_get(resolved_env, "OMNICLAW_GLOBAL_CONFIG_PATH")
    )

    company_entry: CompanyRegistryEntry | None = None
    workspace_root: Path
    resolved_company_config_path: Path | None
    company_settings_payload: dict[str, Any]

    use_global_registry = explicit_workspace_root is None and explicit_company_config_path is None
    if use_global_registry:
        registry = load_global_config(resolved_global_config_path)
        company_entry = resolve_company_reference(registry, explicit_company)
        workspace_root = resolve_company_workspace_root(company_entry.workspace_root)
        if not workspace_root.exists():
            raise FileNotFoundError(
                f"Registered workspace for company '{company_entry.slug}' does not exist: {workspace_root}"
            )
        company_settings_payload = company_entry.to_payload()
        resolved_company_config_path = None
    else:
        # Explicit workspace/config overrides remain available for tests and
        # recovery tooling, but they are not the normal startup contract.
        workspace_root = resolve_company_workspace_root(explicit_workspace_root)
        resolved_company_config_path = resolve_company_config_path(
            workspace_root=workspace_root,
            raw_path=explicit_company_config_path,
        )
        company_settings_payload = _load_legacy_company_settings(resolved_company_config_path)

    resolved_database_url = resolve_database_url(
        workspace_root=workspace_root,
        raw_database_url=database_url if database_url is not None else _env_get(resolved_env, "OMNICLAW_DATABASE_URL"),
    )
    ipc_inbox_rel = (
        _env_get(resolved_env, "OMNICLAW_IPC_INBOX_NEW_REL")
        or _env_get(resolved_env, "OMNICLAW_IPC_INBOX_UNREAD_REL")
        or "inbox/new"
    )

    return Settings(
        app_name=_env_get(resolved_env, "OMNICLAW_APP_NAME") or "omniclaw-kernel",
        environment=_env_get(resolved_env, "OMNICLAW_ENV") or "development",
        log_level=(_env_get(resolved_env, "OMNICLAW_LOG_LEVEL") or "INFO").upper(),
        database_url=resolved_database_url,
        provisioning_mode=(_env_get(resolved_env, "OMNICLAW_PROVISIONING_MODE") or "mock").lower(),
        allow_privileged_provisioning=_parse_bool(
            _env_get(resolved_env, "OMNICLAW_ALLOW_PRIVILEGED_PROVISIONING"),
            default=False,
        ),
        provisioning_helper_path=helper_path.strip() if helper_path else None,
        provisioning_helper_use_sudo=_parse_bool(
            _env_get(resolved_env, "OMNICLAW_PROVISIONING_HELPER_USE_SUDO"),
            default=False,
        ),
        runtime_mode=(_env_get(resolved_env, "OMNICLAW_RUNTIME_MODE") or "mock").lower(),
        allow_privileged_runtime=_parse_bool(
            _env_get(resolved_env, "OMNICLAW_ALLOW_PRIVILEGED_RUNTIME"),
            default=False,
        ),
        runtime_use_sudo=_parse_bool(
            _env_get(resolved_env, "OMNICLAW_RUNTIME_USE_SUDO"),
            default=False,
        ),
        runtime_command_bin=_env_get(resolved_env, "OMNICLAW_RUNTIME_COMMAND_BIN") or "nanobot",
        runtime_gateway_command_template=_env_get(
            resolved_env,
            "OMNICLAW_RUNTIME_GATEWAY_COMMAND_TEMPLATE",
        )
        or "{runtime_bin} gateway --workspace {workspace_root} --config {config_path} --port {port}",
        runtime_command_timeout_seconds=_parse_int(
            _env_get(resolved_env, "OMNICLAW_RUNTIME_COMMAND_TIMEOUT_SECONDS"),
            default=30,
        ),
        runtime_output_boundary_rel=(
            _env_get(resolved_env, "OMNICLAW_RUNTIME_OUTPUT_BOUNDARY_REL") or "drafts/runtime"
        ),
        ipc_queue_paths=_parse_csv_paths(
            _env_get(resolved_env, "OMNICLAW_IPC_QUEUE_PATHS"),
            ("outbox/send", "outbox/pending"),
        ),
        ipc_archive_rel=(_env_get(resolved_env, "OMNICLAW_IPC_ARCHIVE_REL") or "outbox/archive").strip().strip("/"),
        ipc_dead_letter_rel=(
            _env_get(resolved_env, "OMNICLAW_IPC_DEAD_LETTER_REL") or "outbox/dead-letter"
        ).strip().strip("/"),
        ipc_inbox_new_rel=ipc_inbox_rel.strip().strip("/"),
        ipc_router_scan_interval_seconds=_parse_int(
            _env_get(resolved_env, "OMNICLAW_IPC_ROUTER_SCAN_INTERVAL_SECONDS"),
            default=_parse_int_from_mapping(company_settings_payload, ("runtime", "ipc_router_scan_interval_seconds"), 5),
        ),
        ipc_router_auto_scan_enabled=_parse_bool(
            _env_get(resolved_env, "OMNICLAW_IPC_ROUTER_AUTO_SCAN_ENABLED"),
            default=_parse_bool_from_mapping(company_settings_payload, ("runtime", "ipc_router_auto_scan_enabled"), True),
        ),
        budget_auto_cycle_enabled=_parse_bool(
            _env_get(resolved_env, "OMNICLAW_BUDGET_AUTO_CYCLE_ENABLED"),
            default=_parse_bool_from_mapping(company_settings_payload, ("runtime", "budget_auto_cycle_enabled"), True),
        ),
        budget_auto_cycle_poll_interval_seconds=_parse_int(
            _env_get(resolved_env, "OMNICLAW_BUDGET_AUTO_CYCLE_POLL_INTERVAL_SECONDS"),
            default=_parse_int_from_mapping(
                company_settings_payload,
                ("runtime", "budget_auto_cycle_poll_interval_seconds"),
                60,
            ),
        ),
        runtime_retry_scheduler_enabled=_parse_bool(
            _env_get(resolved_env, "OMNICLAW_RUNTIME_RETRY_SCHEDULER_ENABLED"),
            default=_parse_bool_from_mapping(company_settings_payload, ("runtime", "runtime_retry_scheduler_enabled"), True),
        ),
        runtime_retry_scheduler_poll_interval_seconds=_parse_int(
            _env_get(resolved_env, "OMNICLAW_RUNTIME_RETRY_SCHEDULER_POLL_INTERVAL_SECONDS"),
            default=_parse_int_from_mapping(
                company_settings_payload,
                ("runtime", "runtime_retry_scheduler_poll_interval_seconds"),
                60,
            ),
        ),
        global_config_path=str(resolved_global_config_path),
        company_slug=company_entry.slug if company_entry is not None else None,
        company_display_name=company_entry.display_name if company_entry is not None else None,
        company_workspace_root=str(workspace_root),
        company_config_path=str(resolved_company_config_path) if resolved_company_config_path is not None else None,
        company_settings=company_settings_payload,
        litellm_proxy_url=_env_get(resolved_env, "LITELLM_PROXY_URL"),
        litellm_master_key=_env_get(resolved_env, "LITELLM_MASTER_KEY"),
        litellm_auto_start_local_proxy=_parse_bool(
            _env_get(resolved_env, "OMNICLAW_LITELLM_AUTO_START_LOCAL_PROXY"),
            default=True,
        ),
        litellm_local_config_path=_env_get(resolved_env, "OMNICLAW_LITELLM_CONFIG_PATH"),
        litellm_startup_timeout_seconds=_parse_int(
            _env_get(resolved_env, "OMNICLAW_LITELLM_STARTUP_TIMEOUT_SECONDS"),
            default=30,
        ),
    )


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    return build_settings()


def load_effective_company_settings(settings: Settings) -> dict[str, Any]:
    if settings.company_settings:
        return dict(settings.company_settings)
    return _load_legacy_company_settings(
        Path(settings.company_config_path).expanduser().resolve() if settings.company_config_path else None
    )


def _load_legacy_company_settings(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _parse_int_from_mapping(payload: Mapping[str, Any], keys: tuple[str, str], default: int) -> int:
    section = payload.get(keys[0]) if isinstance(payload, Mapping) else None
    if not isinstance(section, Mapping):
        return default
    value = section.get(keys[1])
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_bool_from_mapping(payload: Mapping[str, Any], keys: tuple[str, str], default: bool) -> bool:
    section = payload.get(keys[0]) if isinstance(payload, Mapping) else None
    if not isinstance(section, Mapping):
        return default
    value = section.get(keys[1])
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return _parse_bool(value, default)
    return default
