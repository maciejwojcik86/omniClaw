from dataclasses import dataclass
from functools import lru_cache
from os import getenv
from pathlib import Path

from dotenv import load_dotenv


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
    runtime_gateway_command_template: str = (
        "nanobot gateway --workspace {workspace_root} --config {config_path} --port {port}"
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
    company_config_path: str | None = None
    litellm_proxy_url: str | None = None
    litellm_master_key: str | None = None
    litellm_auto_start_local_proxy: bool = True
    litellm_local_config_path: str | None = None
    litellm_startup_timeout_seconds: int = 30

    @property
    def ipc_inbox_unread_rel(self) -> str:
        return self.ipc_inbox_new_rel


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


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    helper_path = getenv("OMNICLAW_PROVISIONING_HELPER_PATH")
    ipc_inbox_rel = (
        getenv("OMNICLAW_IPC_INBOX_NEW_REL")
        or getenv("OMNICLAW_IPC_INBOX_UNREAD_REL")
        or "inbox/new"
    )
    return Settings(
        app_name=getenv("OMNICLAW_APP_NAME", "omniclaw-kernel"),
        environment=getenv("OMNICLAW_ENV", "development"),
        log_level=getenv("OMNICLAW_LOG_LEVEL", "INFO").upper(),
        database_url=getenv("OMNICLAW_DATABASE_URL", "sqlite:///./workspace/omniclaw.db"),
        provisioning_mode=getenv("OMNICLAW_PROVISIONING_MODE", "mock").lower(),
        allow_privileged_provisioning=_parse_bool(
            getenv("OMNICLAW_ALLOW_PRIVILEGED_PROVISIONING"),
            default=False,
        ),
        provisioning_helper_path=helper_path.strip() if helper_path else None,
        provisioning_helper_use_sudo=_parse_bool(
            getenv("OMNICLAW_PROVISIONING_HELPER_USE_SUDO"),
            default=False,
        ),
        runtime_mode=getenv("OMNICLAW_RUNTIME_MODE", "mock").lower(),
        allow_privileged_runtime=_parse_bool(
            getenv("OMNICLAW_ALLOW_PRIVILEGED_RUNTIME"),
            default=False,
        ),
        runtime_use_sudo=_parse_bool(
            getenv("OMNICLAW_RUNTIME_USE_SUDO"),
            default=False,
        ),
        runtime_gateway_command_template=getenv(
            "OMNICLAW_RUNTIME_GATEWAY_COMMAND_TEMPLATE",
            "nanobot gateway --workspace {workspace_root} --config {config_path} --port {port}",
        ),
        runtime_command_timeout_seconds=_parse_int(
            getenv("OMNICLAW_RUNTIME_COMMAND_TIMEOUT_SECONDS"),
            default=30,
        ),
        runtime_output_boundary_rel=getenv(
            "OMNICLAW_RUNTIME_OUTPUT_BOUNDARY_REL",
            "drafts/runtime",
        ),
        ipc_queue_paths=_parse_csv_paths(
            getenv("OMNICLAW_IPC_QUEUE_PATHS"),
            ("outbox/send", "outbox/pending"),
        ),
        ipc_archive_rel=getenv("OMNICLAW_IPC_ARCHIVE_REL", "outbox/archive").strip().strip("/"),
        ipc_dead_letter_rel=getenv("OMNICLAW_IPC_DEAD_LETTER_REL", "outbox/dead-letter").strip().strip("/"),
        ipc_inbox_new_rel=ipc_inbox_rel.strip().strip("/"),
        ipc_router_scan_interval_seconds=_parse_int(
            getenv("OMNICLAW_IPC_ROUTER_SCAN_INTERVAL_SECONDS"),
            default=5,
        ),
        ipc_router_auto_scan_enabled=_parse_bool(
            getenv("OMNICLAW_IPC_ROUTER_AUTO_SCAN_ENABLED"),
            default=True,
        ),
        budget_auto_cycle_enabled=_parse_bool(
            getenv("OMNICLAW_BUDGET_AUTO_CYCLE_ENABLED"),
            default=True,
        ),
        budget_auto_cycle_poll_interval_seconds=_parse_int(
            getenv("OMNICLAW_BUDGET_AUTO_CYCLE_POLL_INTERVAL_SECONDS"),
            default=60,
        ),
        company_config_path=getenv("OMNICLAW_COMPANY_CONFIG_PATH"),
        litellm_proxy_url=getenv("LITELLM_PROXY_URL"),
        litellm_master_key=getenv("LITELLM_MASTER_KEY"),
        litellm_auto_start_local_proxy=_parse_bool(
            getenv("OMNICLAW_LITELLM_AUTO_START_LOCAL_PROXY"),
            default=True,
        ),
        litellm_local_config_path=getenv("OMNICLAW_LITELLM_CONFIG_PATH"),
        litellm_startup_timeout_seconds=_parse_int(
            getenv("OMNICLAW_LITELLM_STARTUP_TIMEOUT_SECONDS"),
            default=30,
        ),
    )
