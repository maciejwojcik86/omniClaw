from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.db.enums import BudgetMode, NodeStatus, NodeType
from omniclaw.db.models import AgentLLMCall
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_session_factory
from omniclaw.runtime_integration.hook import OmniClawRuntimeIntegration
from tests.helpers import migrate_database_to_head


def test_runtime_integration_records_usage_and_reconciles_budget(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime-integration.db'}"
    migrate_database_to_head(database_url)
    repository = KernelRepository(create_session_factory(database_url))
    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="Director_01",
        status=NodeStatus.ACTIVE,
        linux_username="director_01",
        workspace_root=str((tmp_path / "agent").resolve()),
        runtime_config_path=str((tmp_path / "agent-config.json").resolve()),
        primary_model="openai/gpt-5",
    )
    repository.upsert_budget(
        node_id=node.id,
        budget_mode=BudgetMode.METERED,
        daily_limit_usd=Decimal("10.000000"),
        current_daily_allowance=Decimal("10.000000"),
        current_spend=Decimal("0.000000"),
    )

    integration = OmniClawRuntimeIntegration(database_url=database_url, node_name=node.name)
    started_at = datetime.now(timezone.utc)
    ended_at = started_at + timedelta(seconds=2)
    integration.record_llm_usage(
        usage={
            "prompt_tokens": 12,
            "completion_tokens": 4,
            "reasoning_tokens": 3,
            "total_tokens": 19,
            "cost": "0.123456",
        },
        session_key="cli:test-runtime-hook",
        model="openai/gpt-5",
        provider="LiteLLMProvider",
        started_at=started_at,
        ended_at=ended_at,
        request_context=None,
    )

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        calls = session.query(AgentLLMCall).filter(AgentLLMCall.node_id == node.id).all()
        assert len(calls) == 1
        assert calls[0].session_key == "cli:test-runtime-hook"
        assert calls[0].prompt_tokens == 12
        assert calls[0].completion_tokens == 4
        assert calls[0].reasoning_tokens == 3
        assert calls[0].total_tokens == 19
        assert calls[0].estimated_cost_usd == Decimal("0.123456")

    budget = repository.get_budget(node_id=node.id)
    assert budget is not None
    assert budget.current_spend == Decimal("0.123456")
