from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from fastapi.testclient import TestClient

from omniclaw.app import create_app
from omniclaw.config import Settings
from omniclaw.db.enums import NodeStatus, NodeType
from omniclaw.db.models import AgentTaskRetry
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_session_factory
from omniclaw.runtime.retry_policy import RetryFailureClass
from tests.helpers import migrate_database_to_head


def test_runtime_process_due_retries_claims_and_completes_due_retry(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime-process-retries.db'}"
    workspace_root = tmp_path / "agent-workspace"
    config_path = tmp_path / "agent-config.json"
    workspace_root.mkdir(parents=True, exist_ok=True)
    config_path.write_text("{}", encoding="utf-8")

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
        runtime_mode="mock",
        allow_privileged_runtime=False,
        runtime_use_sudo=False,
        runtime_output_boundary_rel="drafts/runtime",
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="RetryScheduler_01",
        status=NodeStatus.ACTIVE,
        linux_username="retry_scheduler_01",
        workspace_root=str(workspace_root.resolve()),
        runtime_config_path=str(config_path.resolve()),
        primary_model="openrouter/test-model",
    )
    repository.upsert_agent_task_retry(
        node_id=node.id,
        task_key=f"invoke_prompt:{node.id}:cli:retry",
        session_key="cli:retry",
        provider="openrouter",
        model="openrouter/test-model",
        failure_class=RetryFailureClass.TRANSIENT,
        status="pending",
        attempt_count=1,
        max_attempts=8,
        next_attempt_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        last_error_message="429 Too Many Requests",
    )

    client = TestClient(app)
    response = client.post("/v1/runtime/actions", json={"action": "process_due_retries"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["processed_count"] == 1
    assert payload["processed"][0]["status"] == "completed"

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        stored = session.query(AgentTaskRetry).filter(AgentTaskRetry.node_id == node.id).one()
        assert stored.status == "completed"
        assert stored.completed_at is not None


def test_runtime_process_due_retries_replays_original_prompt_payload(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime-process-retries-payload.db'}"
    workspace_root = tmp_path / "agent-workspace-payload"
    config_path = tmp_path / "agent-config-payload.json"
    workspace_root.mkdir(parents=True, exist_ok=True)
    config_path.write_text("{}", encoding="utf-8")

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
        runtime_mode="mock",
        allow_privileged_runtime=False,
        runtime_use_sudo=False,
        runtime_output_boundary_rel="drafts/runtime",
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="RetrySchedulerPayload_01",
        status=NodeStatus.ACTIVE,
        linux_username="retry_scheduler_payload_01",
        workspace_root=str(workspace_root.resolve()),
        runtime_config_path=str(config_path.resolve()),
        primary_model="openrouter/test-model",
    )
    repository.upsert_agent_task_retry(
        node_id=node.id,
        task_key=f"invoke_prompt:{node.id}:cli:retry-payload",
        session_key="cli:retry-payload",
        provider="openrouter",
        model="openrouter/test-model",
        failure_class=RetryFailureClass.BUDGET_RECOVERABLE,
        status="pending",
        attempt_count=1,
        max_attempts=8,
        next_attempt_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        request_payload_json=json.dumps(
            {
                "prompt": "Use the exact original task content",
                "session_key": "cli:retry-payload",
                "markdown": True,
                "include_logs": True,
            }
        ),
        last_error_message="insufficient credits",
    )

    client = TestClient(app)
    response = client.post("/v1/runtime/actions", json={"action": "process_due_retries"})
    assert response.status_code == 200

    run_dir = workspace_root / "drafts" / "runtime" / "runs"
    metadata_files = sorted(run_dir.glob("*.json"))
    assert metadata_files
    metadata = json.loads(metadata_files[-1].read_text(encoding="utf-8"))
    assert "Use the exact original task content" in metadata["command"]
    assert "--markdown" in metadata["command"]
    assert "--logs" in metadata["command"]


def test_repository_claim_agent_task_retry_is_single_claim(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'retry-single-claim.db'}"
    migrate_database_to_head(database_url)
    repository = KernelRepository(create_session_factory(database_url))
    node = repository.create_node(node_type=NodeType.AGENT, name="ClaimNode", status=NodeStatus.ACTIVE)
    repository.upsert_agent_task_retry(
        node_id=node.id,
        task_key="invoke_prompt:claim-test",
        failure_class=RetryFailureClass.TRANSIENT,
        status="pending",
        attempt_count=1,
        max_attempts=8,
        next_attempt_at=datetime.now(timezone.utc),
        last_error_message="429",
    )

    first = repository.claim_agent_task_retry(task_key="invoke_prompt:claim-test")
    second = repository.claim_agent_task_retry(task_key="invoke_prompt:claim-test")
    assert first is not None
    assert first.status == "claimed"
    assert second is None
