from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.config import Settings
from omniclaw.litellm_runtime import _resolve_local_proxy_target, ensure_local_litellm_proxy


def _settings(tmp_path: Path, *, proxy_url: str = "http://127.0.0.1:4000") -> Settings:
    return Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=f"sqlite:///{tmp_path / 'runtime.db'}",
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
        litellm_proxy_url=proxy_url,
        litellm_local_config_path=str(tmp_path / "litellm_config.yaml"),
    )


class _FakeProcess:
    def __init__(self) -> None:
        self.pid = 4321
        self.terminated = False
        self.killed = False
        self._returncode: int | None = None

    def poll(self) -> int | None:
        return self._returncode

    def terminate(self) -> None:
        self.terminated = True
        self._returncode = 0

    def kill(self) -> None:
        self.killed = True
        self._returncode = 9

    def wait(self, timeout: int | None = None) -> int:
        return 0 if self._returncode is None else self._returncode


def test_resolve_local_proxy_target_rejects_remote_urls(tmp_path: Path) -> None:
    settings = _settings(tmp_path, proxy_url="https://openrouter.ai/api/v1")
    assert _resolve_local_proxy_target(settings) is None


def test_ensure_local_litellm_proxy_reuses_healthy_proxy(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    (tmp_path / "litellm_config.yaml").write_text("model_list: []\n", encoding="utf-8")

    monkeypatch.setattr("omniclaw.litellm_runtime._is_proxy_healthy", lambda base_url: True)

    def _unexpected_popen(*args, **kwargs):
        raise AssertionError("proxy should not be started when already healthy")

    monkeypatch.setattr("omniclaw.litellm_runtime.subprocess.Popen", _unexpected_popen)

    with ensure_local_litellm_proxy(settings):
        pass


def test_ensure_local_litellm_proxy_starts_and_stops_proxy(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    config_path = tmp_path / "litellm_config.yaml"
    config_path.write_text("model_list: []\n", encoding="utf-8")
    fake_process = _FakeProcess()
    launched: dict[str, object] = {}

    monkeypatch.setattr("omniclaw.litellm_runtime._is_proxy_healthy", lambda base_url: False)
    monkeypatch.setattr("omniclaw.litellm_runtime._resolve_litellm_command", lambda: ["litellm"])
    monkeypatch.setattr("omniclaw.litellm_runtime._wait_for_proxy_health", lambda **kwargs: True)

    def _fake_popen(command, cwd):
        launched["command"] = command
        launched["cwd"] = cwd
        return fake_process

    monkeypatch.setattr("omniclaw.litellm_runtime.subprocess.Popen", _fake_popen)

    with ensure_local_litellm_proxy(settings):
        assert launched["command"] == [
            "litellm",
            "--host",
            "127.0.0.1",
            "--port",
            "4000",
            "--config",
            str(config_path.resolve()),
        ]

    assert launched["cwd"] == str(ROOT)
    assert fake_process.terminated is True
