from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
import logging
import os
from typing import Any

from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import get_session_factory
from omniclaw.runtime_integration.env import (
    RUNTIME_DATABASE_URL_ENV,
    RUNTIME_NODE_ID_ENV,
    RUNTIME_NODE_NAME_ENV,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class OmniClawRuntimeIntegration:
    database_url: str
    node_id: str | None = None
    node_name: str | None = None
    _repository: KernelRepository = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _, session_factory = get_session_factory(self.database_url)
        self._repository = KernelRepository(session_factory)

    def record_llm_usage(
        self,
        *,
        usage: dict[str, Any] | None,
        session_key: str | None,
        model: str | None,
        provider: str | None,
        started_at: datetime,
        ended_at: datetime,
        request_context: Any | None = None,
    ) -> None:
        del request_context  # reserved for future richer persistence
        if not usage:
            return

        node = self._repository.get_node(node_id=self.node_id, node_name=self.node_name)
        if node is None:
            logger.warning(
                "Skipping runtime usage persistence because node could not be resolved (node_id=%s, node_name=%s)",
                self.node_id,
                self.node_name,
            )
            return

        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        reasoning_tokens = int(usage.get("reasoning_tokens", 0) or 0)
        total_tokens = int(usage.get("total_tokens", 0) or 0)
        estimated_cost_usd = Decimal(str(usage.get("cost", 0) or 0))
        duration_ms = max(int((ended_at - started_at).total_seconds() * 1000), 0)

        self._repository.insert_agent_llm_call(
            node_id=node.id,
            session_key=session_key,
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            start_time=started_at,
            end_time=ended_at,
            duration_ms=duration_ms,
        )

        budget = self._repository.get_budget(node_id=node.id)
        if budget is not None:
            reconciled_spend = self._repository.sum_agent_llm_costs(node_id=node.id)
            self._repository.upsert_budget(node_id=node.id, current_spend=reconciled_spend)


def build_runtime_integration() -> OmniClawRuntimeIntegration | None:
    database_url = (os.getenv(RUNTIME_DATABASE_URL_ENV) or "").strip()
    if not database_url:
        return None

    node_id = (os.getenv(RUNTIME_NODE_ID_ENV) or "").strip() or None
    node_name = (os.getenv(RUNTIME_NODE_NAME_ENV) or "").strip() or None
    return OmniClawRuntimeIntegration(
        database_url=database_url,
        node_id=node_id,
        node_name=node_name,
    )
