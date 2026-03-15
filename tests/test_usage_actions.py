import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, "/home/macos/nanobot")

import pytest
from fastapi.testclient import TestClient
from omniclaw.app import create_app
from omniclaw.config import Settings
from omniclaw.db.models import AgentSessionExport, Node, NodeStatus, NodeType
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_session_factory
from tests.helpers import migrate_database_to_head


@pytest.fixture
def test_setup(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'human.db'}"
    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=db_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(db_url)
    app = create_app(settings)
    session_factory = create_session_factory(db_url)
    client = TestClient(app)
    return client, session_factory


def test_export_agent_session_success(test_setup, tmp_path: Path):
    fast_client, session_factory = test_setup

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    with session_factory() as db_session:
        node = Node(
            type=NodeType.AGENT,
            name="test_exporter_node",
            status=NodeStatus.ACTIVE,
            workspace_root=str(workspace_root),
        )
        db_session.add(node)
        db_session.commit()
        db_session.refresh(node)
        node_id = node.id

    session_key = "cli:test_chat"
    safe_key = "cli_test_chat"
    sessions_dir = workspace_root / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    transcript_file = sessions_dir / f"{safe_key}.jsonl"
    with open(transcript_file, "w") as f:
        f.write(json.dumps({"role": "user", "content": "Hello world!"}) + "\n")
        f.write(json.dumps({"role": "assistant", "content": "Hi there!"}) + "\n")

    response = fast_client.post(
        "/v1/sessions/export",
        json={
            "node_id": node_id,
            "session_key": session_key,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["node_id"] == node_id
    assert data["session_key"] == session_key
    assert data["messages_count"] == 2

    export_path = Path(data["export_path"])
    assert export_path.exists()

    with session_factory() as db_session:
        db_record = db_session.query(AgentSessionExport).filter(AgentSessionExport.node_id == node_id).first()
        assert db_record is not None
        assert db_record.session_key == session_key
        assert db_record.messages_count == 2


def test_export_agent_session_not_found(test_setup, tmp_path: Path):
    fast_client, session_factory = test_setup

    with session_factory() as db_session:
        node = Node(
            type=NodeType.AGENT,
            name="test_missing_node",
            status=NodeStatus.ACTIVE,
            workspace_root=str(tmp_path / "workspace_empty"),
        )
        db_session.add(node)
        db_session.commit()
        db_session.refresh(node)
        node_id = node.id

    response = fast_client.post(
        "/v1/sessions/export",
        json={
            "node_id": node_id,
            "session_key": "cli:ghost_session",
        },
    )

    assert response.status_code == 404


def test_get_session_usage_summary_returns_aggregated_usage(test_setup):
    fast_client, session_factory = test_setup
    repository = KernelRepository(session_factory)
    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="UsageNode_01",
        status=NodeStatus.ACTIVE,
        workspace_root="/tmp/usage-node-01",
    )
    session_key = "usage:test-session"
    repository.insert_agent_llm_call(
        node_id=node.id,
        session_key=session_key,
        model="gpt-test-a",
        provider="openrouter",
        prompt_tokens=10,
        completion_tokens=15,
        reasoning_tokens=2,
        total_tokens=27,
        estimated_cost_usd=0.11,
        start_time=datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 3, 11, 9, 0, 3, tzinfo=timezone.utc),
        duration_ms=3000,
    )
    repository.insert_agent_llm_call(
        node_id=node.id,
        session_key=session_key,
        model="gpt-test-b",
        provider="openrouter",
        prompt_tokens=5,
        completion_tokens=8,
        reasoning_tokens=1,
        total_tokens=14,
        estimated_cost_usd=0.07,
        start_time=datetime(2026, 3, 11, 9, 0, 5, tzinfo=timezone.utc),
        end_time=datetime(2026, 3, 11, 9, 0, 8, tzinfo=timezone.utc),
        duration_ms=3000,
    )

    response = fast_client.get(f"/v1/usage/sessions/{session_key}/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["node_id"] == node.id
    assert payload["node_name"] == "UsageNode_01"
    assert payload["session_key"] == session_key
    assert payload["llm_call_count"] == 2
    assert payload["prompt_tokens"] == 15
    assert payload["completion_tokens"] == 23
    assert payload["reasoning_tokens"] == 3
    assert payload["total_tokens"] == 41
    assert payload["cost_usd"] == pytest.approx(0.18)
    assert payload["session_span_seconds"] == 8.0
    assert payload["provider_breakdown"] == {"openrouter": 2}
    assert payload["model_breakdown"] == {"gpt-test-a": 1, "gpt-test-b": 1}


def test_get_recent_sessions_returns_node_grouped_summaries(test_setup):
    fast_client, session_factory = test_setup
    repository = KernelRepository(session_factory)
    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="RecentNode_01",
        status=NodeStatus.ACTIVE,
        workspace_root="/tmp/recent-node-01",
    )
    repository.insert_agent_llm_call(
        node_id=node.id,
        session_key="session-older",
        total_tokens=20,
        estimated_cost_usd=0.05,
        start_time=datetime(2026, 3, 11, 8, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 3, 11, 8, 0, 2, tzinfo=timezone.utc),
    )
    repository.insert_agent_llm_call(
        node_id=node.id,
        session_key="session-newer",
        total_tokens=30,
        estimated_cost_usd=0.09,
        start_time=datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 3, 11, 9, 0, 4, tzinfo=timezone.utc),
    )
    repository.insert_agent_llm_call(
        node_id=node.id,
        session_key="session-newer",
        total_tokens=10,
        estimated_cost_usd=0.01,
        start_time=datetime(2026, 3, 11, 9, 0, 5, tzinfo=timezone.utc),
        end_time=datetime(2026, 3, 11, 9, 0, 6, tzinfo=timezone.utc),
    )

    response = fast_client.get(f"/v1/usage/nodes/{node.id}/recent-sessions?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["node_id"] == node.id
    assert payload["node_name"] == "RecentNode_01"
    assert [item["session_key"] for item in payload["sessions"]] == ["session-newer", "session-older"]
    assert payload["sessions"][0]["llm_call_count"] == 2
    assert payload["sessions"][0]["total_tokens"] == 40
    assert payload["sessions"][0]["cost_usd"] == pytest.approx(0.10)


def test_get_session_usage_summary_returns_404_when_missing(test_setup):
    fast_client, _session_factory = test_setup

    response = fast_client.get("/v1/usage/sessions/missing-session/summary")

    assert response.status_code == 404
