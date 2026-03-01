from dataclasses import dataclass
from functools import lru_cache
from os import getenv


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


def _parse_bool(raw_value: str | None, default: bool) -> bool:
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    helper_path = getenv("OMNICLAW_PROVISIONING_HELPER_PATH")
    return Settings(
        app_name=getenv("OMNICLAW_APP_NAME", "omniclaw-kernel"),
        environment=getenv("OMNICLAW_ENV", "development"),
        log_level=getenv("OMNICLAW_LOG_LEVEL", "INFO").upper(),
        database_url=getenv("OMNICLAW_DATABASE_URL", "sqlite:///./omniclaw.db"),
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
    )
