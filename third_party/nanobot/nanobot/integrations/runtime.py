from __future__ import annotations

import importlib
import inspect
import os
from typing import Any, Protocol

from loguru import logger

from nanobot.providers.base import LLMRequestContext


class RuntimeIntegration(Protocol):
    def record_llm_usage(
        self,
        *,
        usage: dict[str, Any] | None,
        session_key: str | None,
        model: str | None,
        provider: str | None,
        started_at: Any,
        ended_at: Any,
        request_context: LLMRequestContext | None = None,
    ) -> Any: ...


def load_runtime_integration() -> RuntimeIntegration | None:
    factory_spec = (os.getenv("OMNICLAW_RUNTIME_INTEGRATION_FACTORY") or "").strip()
    if not factory_spec:
        return None

    module_name, separator, attribute_name = factory_spec.partition(":")
    if not separator or not module_name or not attribute_name:
        logger.warning("Invalid runtime integration factory spec: {}", factory_spec)
        return None

    try:
        module = importlib.import_module(module_name)
        factory = getattr(module, attribute_name)
        return factory()
    except Exception as exc:
        logger.warning("Failed to load runtime integration '{}': {}", factory_spec, exc)
        return None


async def maybe_record_llm_usage(
    integration: RuntimeIntegration | None,
    *,
    usage: dict[str, Any] | None,
    session_key: str | None,
    model: str | None,
    provider: str | None,
    started_at: Any,
    ended_at: Any,
    request_context: LLMRequestContext | None = None,
) -> None:
    if integration is None:
        return

    try:
        result = integration.record_llm_usage(
            usage=usage,
            session_key=session_key,
            model=model,
            provider=provider,
            started_at=started_at,
            ended_at=ended_at,
            request_context=request_context,
        )
        if inspect.isawaitable(result):
            await result
    except Exception as exc:
        logger.warning("Failed to record LLM usage via runtime integration: {}", exc)
