from datetime import datetime, timezone
import json
from pathlib import Path

from omniclaw.db.enums import NodeStatus, NodeType
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_session_factory, init_db, create_engine_from_url
from omniclaw.runtime.retry_policy import RetryFailureClass


def test_repository_persists_retry_records_and_failure_telemetry(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'retry-repository.db'}"
    engine = create_engine_from_url(database_url)
    init_db(engine)
    repository = KernelRepository(create_session_factory(database_url))

    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="Retry_Node_01",
        status=NodeStatus.ACTIVE,
    )

    next_attempt_at = datetime(2026, 3, 19, 18, 0, tzinfo=timezone.utc)
    retry = repository.upsert_agent_task_retry(
        node_id=node.id,
        task_key="invoke_prompt:Retry_Node_01:cli:test",
        session_key="cli:test",
        provider="openrouter",
        model="anthropic/claude-sonnet-4",
        failure_class=RetryFailureClass.BUDGET_RECOVERABLE,
        status="pending",
        attempt_count=1,
        max_attempts=8,
        next_attempt_at=next_attempt_at,
        request_payload_json=json.dumps({"prompt": "retry this exact prompt", "session_key": "cli:test"}),
        last_error_message="insufficient credits",
    )

    assert retry.task_key == "invoke_prompt:Retry_Node_01:cli:test"
    assert retry.failure_class == RetryFailureClass.BUDGET_RECOVERABLE
    assert retry.next_attempt_at is not None
    assert retry.next_attempt_at.replace(tzinfo=timezone.utc) == next_attempt_at
    assert json.loads(retry.request_payload_json or "{}")["prompt"] == "retry this exact prompt"

    updated = repository.upsert_agent_task_retry(
        node_id=node.id,
        task_key="invoke_prompt:Retry_Node_01:cli:test",
        session_key="cli:test",
        provider="openrouter",
        model="anthropic/claude-sonnet-4",
        failure_class=RetryFailureClass.TRANSIENT,
        status="pending",
        attempt_count=2,
        max_attempts=8,
        next_attempt_at=next_attempt_at,
        request_payload_json=json.dumps({"prompt": "retry this updated prompt", "session_key": "cli:test"}),
        last_error_message="429 too many requests",
    )
    assert updated.id == retry.id
    assert updated.failure_class == RetryFailureClass.TRANSIENT
    assert updated.attempt_count == 2
    assert json.loads(updated.request_payload_json or "{}")["prompt"] == "retry this updated prompt"

    event = repository.insert_llm_failure_event(
        node_id=node.id,
        task_retry_id=retry.id,
        session_key="cli:test",
        task_key="invoke_prompt:Retry_Node_01:cli:test",
        provider="openrouter",
        model="anthropic/claude-sonnet-4",
        failure_class=RetryFailureClass.TRANSIENT,
        error_message="429 too many requests",
        occurred_at=datetime(2026, 3, 19, 9, 1, tzinfo=timezone.utc),
    )
    assert event.failure_class == RetryFailureClass.TRANSIENT

    events = repository.list_llm_failure_events(provider="openrouter", model="anthropic/claude-sonnet-4")
    assert len(events) == 1
    assert events[0].id == event.id

    summary = repository.summarize_llm_failures_by_provider_model()
    assert len(summary) == 1
    assert summary[0]["provider"] == "openrouter"
    assert summary[0]["model"] == "anthropic/claude-sonnet-4"
    assert summary[0]["failure_class"] == RetryFailureClass.TRANSIENT.value
    assert summary[0]["failure_count"] == 1
