from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from nanobot.providers.base import LLMRequestContext
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.providers.openai_codex_provider import OpenAICodexProvider


def _latest_prompt_log(prompt_logs_root: Path) -> dict[str, object]:
    files = sorted(prompt_logs_root.rglob("*.json"))
    assert files
    return json.loads(files[-1].read_text(encoding="utf-8"))


def test_litellm_provider_writes_prompt_log_without_credentials(
    tmp_path: Path,
    monkeypatch,
) -> None:
    async def fake_completion(**kwargs):
        usage = SimpleNamespace(
            prompt_tokens=11,
            completion_tokens=7,
            total_tokens=18,
            completion_tokens_details=None,
            cost=0.01,
        )
        choice = SimpleNamespace(
            message=SimpleNamespace(content="pong", tool_calls=None, reasoning_content=None),
            finish_reason="stop",
        )
        return SimpleNamespace(choices=[choice], usage=usage)

    monkeypatch.setattr("nanobot.providers.litellm_provider.acompletion", fake_completion)

    prompt_logs_root = tmp_path / "prompt_logs"
    request_context = LLMRequestContext(
        session_key="cli:test",
        call_source="pytest",
        workspace_root=str(tmp_path / "workspace"),
        runtime_output_root=str(tmp_path / "runtime"),
        prompt_logs_root=str(prompt_logs_root),
        node_name="PromptTester",
    )
    provider = LiteLLMProvider(
        api_key="secret-key",
        extra_headers={"Authorization": "Bearer secret"},
        default_model="openai/gpt-5-mini",
    )

    asyncio.run(
        provider.chat(
            messages=[{"role": "system", "content": "System prompt"}, {"role": "user", "content": "Hello"}],
            tools=[{"type": "function", "function": {"name": "noop", "parameters": {}}}],
            model="openai/gpt-5-mini",
            request_context=request_context,
        )
    )

    payload = _latest_prompt_log(prompt_logs_root)
    assert payload["provider"] == "LiteLLMProvider"
    assert payload["session_key"] == "cli:test"
    logged_request = payload["payload"]
    assert logged_request["model"] == "openai/gpt-5-mini"
    assert "messages" in logged_request
    assert "tools" in logged_request
    assert "api_key" not in logged_request
    assert "extra_headers" not in logged_request


def test_codex_provider_writes_prompt_log_without_headers(tmp_path: Path, monkeypatch) -> None:
    async def fake_request_codex(url, headers, body, verify):
        assert "Authorization" in headers
        return "done", [], "stop"

    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider.get_codex_token",
        lambda: SimpleNamespace(account_id="acct", access="super-secret"),
    )
    monkeypatch.setattr("nanobot.providers.openai_codex_provider._request_codex", fake_request_codex)

    prompt_logs_root = tmp_path / "prompt_logs"
    request_context = LLMRequestContext(
        session_key="cli:codex",
        call_source="pytest",
        workspace_root=str(tmp_path / "workspace"),
        runtime_output_root=str(tmp_path / "runtime"),
        prompt_logs_root=str(prompt_logs_root),
        node_name="CodexTester",
    )
    provider = OpenAICodexProvider(default_model="openai-codex/gpt-5.1-codex")

    asyncio.run(
        provider.chat(
            messages=[{"role": "system", "content": "System prompt"}, {"role": "user", "content": "Hello"}],
            model="openai-codex/gpt-5.1-codex",
            request_context=request_context,
        )
    )

    payload = _latest_prompt_log(prompt_logs_root)
    assert payload["provider"] == "OpenAICodexProvider"
    logged_request = payload["payload"]
    assert logged_request["instructions"] == "System prompt"
    assert logged_request["input"][0]["role"] == "user"
    assert "Authorization" not in json.dumps(logged_request)
