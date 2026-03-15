from __future__ import annotations

from contextlib import contextmanager
import logging
from pathlib import Path
import os
import shutil
import subprocess
import sys
import time
from typing import Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from omniclaw.config import REPO_ROOT, Settings


_LOCAL_PROXY_HOSTS = {"127.0.0.1", "localhost"}


def _resolve_local_proxy_target(settings: Settings) -> tuple[str, int, str] | None:
    if not settings.litellm_auto_start_local_proxy or not settings.litellm_proxy_url:
        return None
    parsed = urlparse(settings.litellm_proxy_url)
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.hostname not in _LOCAL_PROXY_HOSTS:
        return None
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return parsed.hostname, port, settings.litellm_proxy_url.rstrip("/")


def _resolve_litellm_command() -> list[str]:
    script_path = Path(sys.executable).resolve().parent / "litellm"
    if script_path.is_file():
        return [str(script_path)]
    resolved = shutil.which("litellm")
    if resolved:
        return [resolved]
    return ["uv", "run", "litellm"]


def _resolve_config_path(settings: Settings) -> Path:
    raw_path = settings.litellm_local_config_path or str(REPO_ROOT / "litellm_config.yaml")
    return Path(raw_path).expanduser().resolve()


def _health_url(base_url: str) -> str:
    return f"{base_url}/health/liveliness"


def _is_proxy_healthy(base_url: str, *, timeout_seconds: float = 1.0) -> bool:
    try:
        with urlopen(_health_url(base_url), timeout=timeout_seconds) as response:
            return 200 <= getattr(response, "status", 200) < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def _wait_for_proxy_health(
    *,
    process: subprocess.Popen[bytes] | subprocess.Popen[str],
    base_url: str,
    timeout_seconds: int,
) -> bool:
    deadline = time.monotonic() + max(1, timeout_seconds)
    while time.monotonic() < deadline:
        if _is_proxy_healthy(base_url):
            return True
        if process.poll() is not None:
            return False
        time.sleep(1)
    return _is_proxy_healthy(base_url)


@contextmanager
def ensure_local_litellm_proxy(
    settings: Settings,
    *,
    logger: logging.Logger | None = None,
) -> Iterator[None]:
    target = _resolve_local_proxy_target(settings)
    if target is None:
        yield
        return

    host, port, base_url = target
    if _is_proxy_healthy(base_url):
        if logger is not None:
            logger.info("LiteLLM proxy already healthy at %s", base_url)
        yield
        return

    config_path = _resolve_config_path(settings)
    if not config_path.is_file():
        raise RuntimeError(
            "LiteLLM auto-start is enabled, but the config file was not found at "
            f"{config_path}"
        )

    command = [
        *_resolve_litellm_command(),
        "--host",
        host,
        "--port",
        str(port),
        "--config",
        str(config_path),
    ]
    if logger is not None:
        logger.info("Starting local LiteLLM proxy at %s", base_url)

    process = subprocess.Popen(command, cwd=str(REPO_ROOT))
    try:
        if not _wait_for_proxy_health(
            process=process,
            base_url=base_url,
            timeout_seconds=settings.litellm_startup_timeout_seconds,
        ):
            raise RuntimeError(
                "LiteLLM did not become healthy at "
                f"{base_url} within {settings.litellm_startup_timeout_seconds}s"
            )
        yield
    finally:
        if process.poll() is None:
            if logger is not None:
                logger.info("Stopping local LiteLLM proxy pid=%s", process.pid)
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
