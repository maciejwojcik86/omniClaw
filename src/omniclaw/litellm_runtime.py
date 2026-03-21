from __future__ import annotations

"""Runtime helpers for making a local LiteLLM proxy available on demand.

This module is used by the OmniClaw CLI startup path in
`src/omniclaw/cli.py`. The CLI wraps `uvicorn.run(...)` in
`ensure_local_litellm_proxy(...)` so the kernel can rely on a healthy local
LiteLLM proxy when the selected settings say "auto-start one for me".

The helpers in this file are intentionally narrow:
- decide whether the configured proxy target is a local process we should own
- find the right `litellm` command and config file
- wait for the proxy to report healthy before continuing startup
- tear it down again when the wrapped block exits

Tests in `tests/test_litellm_runtime.py` cover the two main behaviors:
reusing an already-healthy proxy and starting/stopping one when needed.
"""

from contextlib import contextmanager
import logging
from pathlib import Path
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
    """Return the local LiteLLM host/port/base URL if OmniClaw should manage it.

    Why this exists:
    OmniClaw may talk to either a remote LiteLLM-compatible endpoint or a
    locally hosted LiteLLM proxy. Auto-starting only makes sense for a local
    proxy that this process can own, so this function acts as the gatekeeper.

    Where it is used:
    `ensure_local_litellm_proxy()` calls this first. If it returns `None`, the
    context manager becomes a no-op and the caller proceeds without trying to
    launch anything.
    """
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
    """Choose the best command for launching the LiteLLM proxy process.

    Why this exists:
    developers may run OmniClaw from different environments. Sometimes the
    `litellm` executable lives next to the active Python interpreter, sometimes
    it is on `PATH`, and sometimes the safest fallback is `uv run litellm`.

    Where it is used:
    `ensure_local_litellm_proxy()` uses this only when it has decided a new
    local proxy process must be started.
    """
    script_path = Path(sys.executable).resolve().parent / "litellm"
    if script_path.is_file():
        return [str(script_path)]
    resolved = shutil.which("litellm")
    if resolved:
        return [resolved]
    return ["uv", "run", "litellm"]


def _resolve_config_path(settings: Settings) -> Path:
    """Resolve the LiteLLM config path used for a locally started proxy.

    Why this exists:
    the proxy process needs a config file describing models and routing. This
    keeps the lookup rules in one place so startup logic stays readable.

    Where it is used:
    `ensure_local_litellm_proxy()` calls this before spawning the proxy and
    raises a clear runtime error if the file is missing.
    """
    raw_path = settings.litellm_local_config_path or str(REPO_ROOT / "litellm_config.yaml")
    return Path(raw_path).expanduser().resolve()


def _health_url(base_url: str) -> str:
    """Build the health endpoint URL exposed by the LiteLLM proxy."""
    return f"{base_url}/health/liveliness"


def _is_proxy_healthy(base_url: str, *, timeout_seconds: float = 1.0) -> bool:
    """Return whether the proxy responds successfully to its health endpoint.

    Why this exists:
    the startup flow needs a cheap readiness check both before launch
    ("is something already running?") and after launch ("is the new process
    actually ready to serve requests yet?").

    Where it is used:
    `ensure_local_litellm_proxy()` uses it for the fast-path reuse check, and
    `_wait_for_proxy_health()` uses it while polling during startup.
    """
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
    """Poll until the proxy is healthy, the process exits, or time runs out.

    Why this exists:
    launching a subprocess only means "the OS accepted the command", not "the
    HTTP server is ready". This function bridges that gap so the CLI does not
    continue into kernel startup until LiteLLM is actually reachable.

    Where it is used:
    `ensure_local_litellm_proxy()` calls it immediately after `subprocess.Popen`.
    """
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
    """Ensure a local LiteLLM proxy is running for the duration of a code block.

    Why this exists:
    the OmniClaw CLI uses this as a guard around `uvicorn.run(...)` in
    `src/omniclaw/cli.py`. That gives the kernel a simple contract: if settings
    say to auto-start a local proxy, the proxy will be healthy before the server
    starts accepting work, and it will be cleaned up on exit.

    Behavior summary:
    - If auto-start is disabled or the configured proxy URL is not local, do
      nothing.
    - If a healthy local proxy already exists, reuse it and leave ownership to
      whatever started it.
    - Otherwise, start a new LiteLLM subprocess, wait for readiness, yield to
      the caller, then stop the subprocess on the way out.

    Tests:
    `tests/test_litellm_runtime.py` covers the reuse path and the
    start/wait/stop path.
    """
    target = _resolve_local_proxy_target(settings)
    if target is None:
        yield
        return

    host, port, base_url = target
    # Reuse an already-running local proxy instead of taking over its lifecycle.
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

    # OmniClaw owns this subprocess only in the branch where it had to launch it.
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
                # Escalate to a hard kill so shutdown does not hang indefinitely.
                process.kill()
                process.wait(timeout=5)
