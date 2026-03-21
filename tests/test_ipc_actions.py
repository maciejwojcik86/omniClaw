import os
from pathlib import Path
import sys
import time
import json
import shutil
import stat
import subprocess
import threading

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.app import create_app
from omniclaw.config import Settings
from omniclaw.db.enums import FormStatus, NodeStatus, NodeType
from omniclaw.db.models import FormLedger, FormTransitionEvent
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_session_factory
from omniclaw.forms.service import FormsService
from omniclaw.ipc.schemas import IpcActionRequest
from omniclaw.ipc.service import IpcRouterService
from tests.helpers import migrate_database_to_head


def _seed_company_workspace(company_root: Path) -> None:
    (company_root / "master_skills").mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "tests" / "fixtures" / "message-form", company_root / "forms" / "message", dirs_exist_ok=True)
    shutil.copytree(
        ROOT / "tests" / "fixtures" / "nanobot_workspace_templates",
        company_root / "nanobot_workspace_templates",
        dirs_exist_ok=True,
    )


def _ensure_workspace_dirs(workspace_root: Path) -> None:
    _seed_company_workspace(workspace_root.parent)
    for relative in (
        "inbox/new",
        "inbox/read",
        "outbox/send",
        "outbox/archive",
        "outbox/dead-letter",
        "outbox/drafts",
    ):
        (workspace_root / relative).mkdir(parents=True, exist_ok=True)


def _seed_form_stage_skills(*, workspace_root: Path, form_type: str, skill_names: list[str]) -> None:
    for skill_name in skill_names:
        skill_dir = workspace_root / "forms" / form_type / "skills" / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"# {skill_name}\n\nTest fixture skill package.\n",
            encoding="utf-8",
        )


def _write_inbox_wake_prompt(workspace_root: Path, content: str | None = None) -> None:
    prompt_path = workspace_root / "NEW_INBOX_MESSAGE_PROMPT.md"
    prompt_path.write_text(
        content
        or (
            "Read the newly delivered form at {{delivery_path}}.\n\n"
            "Form type: {{form_type}}\n"
            "Stage: {{stage}}\n"
            "Required skill: {{stage_skill}}\n"
            "Sender: {{sender_name}}\n"
            "Subject: {{subject}}\n"
        ),
        encoding="utf-8",
    )


def _write_message_file(
    *,
    queue_file: Path,
    sender: str | None,
    target: str,
    subject: str | None,
    frontmatter_name: str | None = None,
    decision: str | None = "send",
    use_legacy_transition_field: bool = False,
) -> None:
    frontmatter = ["---", "type: MESSAGE", f"target: {target}"]
    if decision is not None:
        decision_field = "transition" if use_legacy_transition_field else "decision"
        frontmatter.append(f"{decision_field}: {decision}")
    if sender is not None:
        frontmatter.insert(2, f"sender: {sender}")
    if subject is not None:
        frontmatter.append(f"subject: {subject}")
    if frontmatter_name is not None:
        frontmatter.append(f"name: {frontmatter_name}")
    frontmatter.append("---")
    payload = "\n".join(frontmatter) + "\n\nHello from OmniClaw.\n"
    queue_file.write_text(payload, encoding="utf-8")


def _write_generic_form_file(
    *,
    queue_file: Path,
    form_type: str,
    stage: str,
    decision: str,
    target: str | None,
    stage_skill: str | None = None,
    subject: str | None = None,
    use_legacy_transition_field: bool = False,
) -> None:
    decision_field = "transition" if use_legacy_transition_field else "decision"
    frontmatter = [
        "---",
        f"form_type: {form_type}",
        f"stage: {stage}",
        f"{decision_field}: {decision}",
    ]
    if stage_skill is not None:
        frontmatter.append(f"stage_skill: {stage_skill}")
    if target is not None:
        frontmatter.append(f"target: {target}")
    if subject is not None:
        frontmatter.append(f"subject: {subject}")
    frontmatter.append("---")
    payload = "\n".join(frontmatter) + "\n\nHello from OmniClaw.\n"
    queue_file.write_text(payload, encoding="utf-8")


def _parse_frontmatter_content(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith("---\n"):
        raise AssertionError("expected markdown frontmatter opening delimiter")
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError("invalid frontmatter opening delimiter")

    closing_index: int | None = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break
    if closing_index is None:
        raise AssertionError("missing frontmatter closing delimiter")

    frontmatter: dict[str, str] = {}
    current_block_key: str | None = None
    current_block_lines: list[str] = []

    def flush_block() -> None:
        nonlocal current_block_key, current_block_lines
        if current_block_key is None:
            return
        frontmatter[current_block_key] = "\n".join(current_block_lines).rstrip("\n")
        current_block_key = None
        current_block_lines = []

    for line in lines[1:closing_index]:
        if current_block_key is not None:
            if line.startswith("  "):
                current_block_lines.append(line[2:])
                continue
            if line == "":
                current_block_lines.append("")
                continue
            flush_block()

        stripped = line.strip()
        if not stripped:
            continue
        if ":" not in stripped:
            raise AssertionError(f"invalid frontmatter line: '{line}'")
        key, value = stripped.split(":", 1)
        normalized_key = key.strip()
        normalized_value = value.strip().strip('"').strip("'")
        if normalized_value in {"|", "|-", "|+"}:
            current_block_key = normalized_key
            current_block_lines = []
            continue
        frontmatter[normalized_key] = normalized_value

    flush_block()

    body = "\n".join(lines[closing_index + 1 :])
    return frontmatter, body


def _load_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    return _parse_frontmatter_content(path.read_text(encoding="utf-8"))


def _render_with_frontmatter(*, frontmatter: dict[str, str], body: str) -> str:
    lines = ["---"]
    for key, value in frontmatter.items():
        if "\n" in value:
            lines.append(f"{key}: |")
            for value_line in value.split("\n"):
                lines.append(f"  {value_line}")
            continue
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.rstrip("\n") + "\n"


def test_ipc_scan_routes_authorized_message_within_target_window(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'ipc-route.db'}"
    worker_workspace = tmp_path / "worker-workspace"
    manager_workspace = tmp_path / "manager-workspace"
    _ensure_workspace_dirs(worker_workspace)
    _ensure_workspace_dirs(manager_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    manager = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Manager_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(manager_workspace.resolve()),
    )
    worker = repository.create_node(
        node_type=NodeType.AGENT,
        name="Worker_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(worker_workspace.resolve()),
    )
    repository.link_manager(parent_node_id=manager.id, child_node_id=worker.id)

    queue_file = worker_workspace / "outbox" / "send" / "status-update.md"
    _write_message_file(
        queue_file=queue_file,
        sender="Worker_01",
        target="Manager_01",
        subject="Daily status",
    )

    client = TestClient(app)
    started = time.monotonic()
    response = client.post("/v1/ipc/actions", json={"action": "scan_messages"})
    finished = time.monotonic()

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["scanned"] == 1
    assert payload["summary"]["routed"] == 1
    assert payload["summary"]["undelivered"] == 0
    assert payload["summary"]["duration_ms"] <= 5000
    assert (finished - started) <= 5
    assert payload["items"][0]["decision"] == "send"
    assert "transition" not in payload["items"][0]

    delivered = manager_workspace / "inbox" / "new" / "status-update.md"
    archived = worker_workspace / "outbox" / "archive" / "status-update.md"
    assert delivered.exists()
    assert archived.exists()
    assert queue_file.exists() is False
    assert bool(delivered.stat().st_mode & stat.S_IWGRP)
    assert bool(archived.stat().st_mode & stat.S_IWGRP)
    delivered_text = delivered.read_text(encoding="utf-8")
    assert "decision:" in delivered_text
    assert "agent: Manager_01" in delivered_text
    assert "stage_skill: read-and-acknowledge-internal-message" in delivered_text
    assert "transition:" not in delivered_text
    assert "initiator_node_id:" not in delivered_text
    assert "target_node_id:" not in delivered_text
    assert "in_reply_to:" not in delivered_text
    delivered_frontmatter, _ = _load_frontmatter(delivered)
    assert delivered_frontmatter["agent"] == "Manager_01"
    assert delivered_frontmatter["target"] == ""
    assert delivered_frontmatter["target_agent"] == ""

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        form = session.query(FormLedger).order_by(FormLedger.created_at.asc()).first()
        assert form is not None
        assert form.type == "message"
        assert form.form_type_key == "message"
        assert form.current_status == FormStatus.WAITING_TO_BE_READ.value


def test_ipc_scan_triggers_agent_wake_after_delivery(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'ipc-wake.db'}"
    sender_workspace = tmp_path / "sender-workspace"
    agent_workspace = tmp_path / "agent-workspace"
    _ensure_workspace_dirs(sender_workspace)
    _ensure_workspace_dirs(agent_workspace)
    _write_inbox_wake_prompt(tmp_path)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
        runtime_mode="mock",
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    repository.create_node(
        node_type=NodeType.HUMAN,
        name="Manager_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(sender_workspace.resolve()),
    )
    repository.create_node(
        node_type=NodeType.AGENT,
        name="Worker_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(agent_workspace.resolve()),
        runtime_config_path=str((tmp_path / "worker-config.json").resolve()),
    )

    queue_file = sender_workspace / "outbox" / "send" / "status-update.md"
    _write_message_file(
        queue_file=queue_file,
        sender="Manager_01",
        target="Worker_01",
        subject="Daily status",
    )

    client = TestClient(app)
    response = client.post("/v1/ipc/actions", json={"action": "scan_messages"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["routed"] == 1
    item = payload["items"][0]
    assert item["status"] == "routed"
    assert item["wake_trigger"]["status"] == "triggered"
    assert item["wake_trigger"]["prompt_path"] == str((tmp_path / "NEW_INBOX_MESSAGE_PROMPT.md").resolve())
    assert item["wake_trigger"]["session_key"] == "ipc:auto-wake:Worker_01:status-update"
    assert "mock reply from Worker_01" in str(item["wake_trigger"]["reply"])


def test_ipc_scan_claims_pending_form_under_concurrent_scans(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'ipc-concurrent-route.db'}"
    worker_workspace = tmp_path / "worker-workspace"
    manager_workspace = tmp_path / "manager-workspace"
    _ensure_workspace_dirs(worker_workspace)
    _ensure_workspace_dirs(manager_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    repository = KernelRepository(create_session_factory(database_url))
    manager = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Manager_Concurrent_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(manager_workspace.resolve()),
    )
    worker = repository.create_node(
        node_type=NodeType.AGENT,
        name="Worker_Concurrent_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(worker_workspace.resolve()),
    )
    repository.link_manager(parent_node_id=manager.id, child_node_id=worker.id)

    queue_file = worker_workspace / "outbox" / "send" / "status-update.md"
    _write_message_file(
        queue_file=queue_file,
        sender="Worker_Concurrent_01",
        target="Manager_Concurrent_01",
        subject="Concurrent status",
    )

    service = IpcRouterService(settings=settings, repository=repository)
    barrier = threading.Barrier(2)
    results: list[dict[str, object] | None] = [None, None]
    errors: list[Exception | None] = [None, None]

    def run_scan(index: int) -> None:
        try:
            barrier.wait(timeout=5)
            results[index] = service.execute(IpcActionRequest(action="scan_forms"))
        except Exception as exc:  # pragma: no cover - failure path asserted below
            errors[index] = exc

    first = threading.Thread(target=run_scan, args=(0,))
    second = threading.Thread(target=run_scan, args=(1,))
    first.start()
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == [None, None]
    assert results[0] is not None
    assert results[1] is not None

    total_scanned = sum(int(result["summary"]["scanned"]) for result in results if result is not None)
    total_routed = sum(int(result["summary"]["routed"]) for result in results if result is not None)
    total_undelivered = sum(int(result["summary"]["undelivered"]) for result in results if result is not None)
    assert total_scanned == 1
    assert total_routed == 1
    assert total_undelivered == 0

    delivered = manager_workspace / "inbox" / "new" / "status-update.md"
    archived = worker_workspace / "outbox" / "archive" / "status-update.md"
    assert delivered.exists()
    assert archived.exists()
    assert queue_file.exists() is False

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        form = session.query(FormLedger).filter(FormLedger.message_name == "status-update.md").one_or_none()
        assert form is not None
        assert form.current_status == FormStatus.WAITING_TO_BE_READ.value
        events = (
            session.query(FormTransitionEvent)
            .filter(FormTransitionEvent.form_id == form.form_id)
            .order_by(FormTransitionEvent.sequence.asc())
            .all()
        )
        assert [event.to_status for event in events] == [
            FormStatus.DRAFT.value,
            FormStatus.WAITING_TO_BE_READ.value,
        ]
        assert form.sender_node_id == worker.id
        assert form.target_node_id == manager.id
        assert form.subject == "Concurrent status"
        assert form.delivery_path is not None
        assert form.archive_path is not None


def test_ipc_scan_routes_message_without_management_link(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'ipc-any-target.db'}"
    sender_workspace = tmp_path / "sender-workspace"
    target_workspace = tmp_path / "target-workspace"
    _ensure_workspace_dirs(sender_workspace)
    _ensure_workspace_dirs(target_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    repository.create_node(
        node_type=NodeType.AGENT,
        name="Sender_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(sender_workspace.resolve()),
    )
    repository.create_node(
        node_type=NodeType.AGENT,
        name="Target_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(target_workspace.resolve()),
    )

    queue_file = sender_workspace / "outbox" / "send" / "request.md"
    _write_message_file(
        queue_file=queue_file,
        sender="Sender_01",
        target="Target_01",
        subject="Need review",
    )

    client = TestClient(app)
    response = client.post("/v1/ipc/actions", json={"action": "scan_messages"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["scanned"] == 1
    assert payload["summary"]["routed"] == 1
    assert payload["summary"]["undelivered"] == 0

    archived = sender_workspace / "outbox" / "archive" / "request.md"
    delivered = target_workspace / "inbox" / "new" / "request.md"
    assert archived.exists()
    assert delivered.exists()

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        form = session.query(FormLedger).order_by(FormLedger.created_at.asc()).first()
        assert form is not None
        assert form.current_status == FormStatus.WAITING_TO_BE_READ.value
        assert form.failure_reason is None


def test_ipc_scan_accepts_legacy_frontmatter_transition_field(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'ipc-legacy-frontmatter-transition.db'}"
    sender_workspace = tmp_path / "sender-workspace"
    target_workspace = tmp_path / "target-workspace"
    _ensure_workspace_dirs(sender_workspace)
    _ensure_workspace_dirs(target_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    repository.create_node(
        node_type=NodeType.AGENT,
        name="Sender_Legacy",
        status=NodeStatus.ACTIVE,
        workspace_root=str(sender_workspace.resolve()),
    )
    repository.create_node(
        node_type=NodeType.AGENT,
        name="Target_Legacy",
        status=NodeStatus.ACTIVE,
        workspace_root=str(target_workspace.resolve()),
    )

    queue_file = sender_workspace / "outbox" / "send" / "legacy-frontmatter.md"
    _write_message_file(
        queue_file=queue_file,
        sender="Sender_Legacy",
        target="Target_Legacy",
        subject="Legacy decision field",
        use_legacy_transition_field=True,
    )

    client = TestClient(app)
    response = client.post("/v1/ipc/actions", json={"action": "scan_messages"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["scanned"] == 1
    assert payload["summary"]["routed"] == 1
    assert payload["summary"]["undelivered"] == 0
    assert payload["items"][0]["decision"] == "send"
    assert "transition" not in payload["items"][0]

    delivered = target_workspace / "inbox" / "new" / "legacy-frontmatter.md"
    assert delivered.exists()
    delivered_text = delivered.read_text(encoding="utf-8")
    assert "decision:" in delivered_text
    assert "stage_skill: read-and-acknowledge-internal-message" in delivered_text
    assert "transition:" not in delivered_text


def test_ipc_scan_uses_active_custom_form_type_definition(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspace"
    monkeypatch.setattr(FormsService, "_workspace_root", lambda self: workspace_root)
    monkeypatch.setattr(IpcRouterService, "_workspace_forms_root", lambda self: workspace_root / "forms")
    monkeypatch.setattr(IpcRouterService, "_workspace_form_archive_root", lambda self: workspace_root / "form_archive")
    _seed_form_stage_skills(
        workspace_root=workspace_root,
        form_type="custom_message_form",
        skill_names=[
            "draft_internal_message",
            "read_and_acknowledge_internal_message",
            "archive_internal_message",
        ],
    )

    database_url = f"sqlite:///{tmp_path / 'ipc-custom-message-type.db'}"
    sender_workspace = tmp_path / "sender-workspace"
    target_workspace = tmp_path / "target-workspace"
    _ensure_workspace_dirs(sender_workspace)
    _ensure_workspace_dirs(target_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    sender = repository.create_node(
        node_type=NodeType.AGENT,
        name="Sender_Custom",
        status=NodeStatus.ACTIVE,
        workspace_root=str(sender_workspace.resolve()),
    )
    target = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Target_Custom",
        status=NodeStatus.ACTIVE,
        workspace_root=str(target_workspace.resolve()),
    )

    client = TestClient(app)
    upsert_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "upsert_form_type",
            "type_key": "custom_message_form",
            "version": "2.0.0",
            "workflow_graph": {
                "start_stage": "DRAFT",
                "end_stage": "READ_ARCHIVED",
                "dispatch_decision": "dispatch_to_target",
                "acknowledge_decision": "mark_read",
                "stages": {
                    "DRAFT": {
                        "target": "{{initiator}}",
                        "required_skill": "draft_internal_message",
                        "decisions": {
                            "dispatch_to_target": "INBOX_UNREAD",
                        },
                    },
                    "INBOX_UNREAD": {
                        "target": "{{any}}",
                        "required_skill": "read_and_acknowledge_internal_message",
                        "decisions": {
                            "mark_read": "READ_ARCHIVED",
                        },
                    },
                    "READ_ARCHIVED": {
                        "target": None,
                        "required_skill": "archive_internal_message",
                        "is_terminal": True,
                    }
                },
            },
            "stage_metadata": {},
        },
    )
    assert upsert_response.status_code == 200
    assert upsert_response.json()["validation_errors"] == []

    activate_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "activate_form_type",
            "type_key": "custom_message_form",
            "version": "2.0.0",
        },
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["form_type"]["version"] == "2.0.0"

    definitions = repository.list_form_type_definitions(type_key="custom_message_form")
    assert len(definitions) == 1
    assert definitions[0].version == "2.0.0"
    assert definitions[0].lifecycle_state.value == "ACTIVE"

    queue_file = sender_workspace / "outbox" / "send" / "custom-message.md"
    _write_generic_form_file(
        queue_file=queue_file,
        form_type="custom_message_form",
        stage="DRAFT",
        decision="dispatch_to_target",
        target="Target_Custom",
        subject="Custom workflow",
    )
    scan_response = client.post("/v1/ipc/actions", json={"action": "scan_messages"})
    assert scan_response.status_code == 200
    payload = scan_response.json()
    assert payload["summary"]["routed"] == 1
    assert payload["items"][0]["decision"] == "dispatch_to_target"
    assert "transition" not in payload["items"][0]
    form_id = payload["items"][0]["form_id"]

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        form = session.query(FormLedger).filter(FormLedger.form_id == form_id).first()
        assert form is not None
        assert form.form_type_key == "custom_message_form"
        assert form.form_type_version == "2.0.0"
        assert form.current_status == "INBOX_UNREAD"
        assert form.current_holder_node == target.id

    delivered = target_workspace / "inbox" / "new" / "custom-message.md"
    read_copy = target_workspace / "inbox" / "read" / "custom-message.md"
    assert delivered.exists()
    delivered_frontmatter, _ = _load_frontmatter(delivered)
    assert delivered_frontmatter["agent"] == "Target_Custom"
    assert delivered_frontmatter["stage_skill"] == "read_and_acknowledge_internal_message"
    assert delivered_frontmatter["target"] == ""
    assert delivered_frontmatter["target_agent"] == ""
    delivered.rename(read_copy)

    ack_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "transition_form",
            "form_id": form_id,
            "actor_node_id": target.id,
            "decision_key": "mark_read",
            "payload": {
                "new_path": str(delivered),
                "read_path": str(read_copy),
            },
        },
    )
    assert ack_response.status_code == 200
    assert ack_response.json()["form"]["current_status"] == "READ_ARCHIVED"
    assert ack_response.json()["form"]["current_holder_node"] is None


def test_ipc_scan_routes_deploy_new_agent_full_stage_cycle(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspace"
    forms_root = workspace_root / "forms" / "deploy_new_agent"
    skills_root = forms_root / "skills"
    archive_root = workspace_root / "form_archive"
    skill_descriptions = {
        "draft-agent-business-case": "Draft BUSINESS_CASE details for deployment request.",
        "review-agent-role-and-template": (
            "Perform HR_REVIEW for deploy_new_agent forms and decide whether to move to finance or return for "
            "revision."
        ),
        "allocate-agent-budget": (
            "Perform FINANCE_REVIEW for deploy_new_agent and decide whether budget is approved or returned to HR."
        ),
        "final-agent-signoff": (
            "Execute DIRECTOR_APPROVAL for deploy_new_agent and choose deployment, rework, or rejection."
        ),
        "deploy-new-nanobot": (
            "Deploy a repo-local Nanobot agent under workspace/agents/<agent_name>/ with sibling config.json, "
            "workspace scaffold, AGENTS.md instructions, kernel provisioning trigger, and Nanobot smoke commands."
        ),
    }
    for skill_name, skill_description in skill_descriptions.items():
        skill_dir = skills_root / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            (
                "---\n"
                f"name: {skill_name}\n"
                f"description: {skill_description}\n"
                "---\n\n"
                "# skill\n"
            ),
            encoding="utf-8",
        )
        if skill_name == "deploy-new-nanobot":
            source_skill_dir = ROOT / "tests" / "fixtures" / "deploy-new-nanobot-skill"
            for child in source_skill_dir.iterdir():
                if child.name == "SKILL.md":
                    continue
                destination = skill_dir / child.name
                if child.is_dir():
                    shutil.copytree(child, destination, dirs_exist_ok=True)
                else:
                    shutil.copy2(child, destination)

    workflow_payload = {
        "form_type": "deploy_new_agent",
        "version": "9.9.9",
        "description": "Deploy workflow fixture",
        "start_stage": "BUSINESS_CASE",
        "end_stage": "ARCHIVED",
        "stages": {
            "BUSINESS_CASE": {
                "target": "{{initiator}}",
                "required_skill": "draft-agent-business-case",
                "decisions": {"submit_to_hr": "HR_REVIEW"},
            },
            "HR_REVIEW": {
                "target": "HR_Head_01",
                "required_skill": "review-agent-role-and-template",
                "decisions": {"approve_to_finance": "FINANCE_REVIEW"},
            },
            "FINANCE_REVIEW": {
                "target": "Macos_Supervisor",
                "required_skill": "allocate-agent-budget",
                "decisions": {"approve_to_director": "DIRECTOR_APPROVAL"},
            },
            "DIRECTOR_APPROVAL": {
                "target": "Director_01",
                "required_skill": "final-agent-signoff",
                "decisions": {"execute_deployment": "AGENT_DEPLOYMENT"},
            },
            "AGENT_DEPLOYMENT": {
                "target": "Ops_Head_01",
                "required_skill": "deploy-new-nanobot",
                "decisions": {"deploy_and_archive": "ARCHIVED"},
            },
            "ARCHIVED": {
                "target": None,
                "is_terminal": True,
            },
        },
    }
    forms_root.mkdir(parents=True, exist_ok=True)
    (forms_root / "workflow.json").write_text(json.dumps(workflow_payload, indent=2) + "\n", encoding="utf-8")

    monkeypatch.setattr(FormsService, "_workspace_root", lambda self: workspace_root)
    monkeypatch.setattr(FormsService, "_workspace_forms_root", lambda self: workspace_root / "forms")
    monkeypatch.setattr(IpcRouterService, "_workspace_forms_root", lambda self: workspace_root / "forms")
    monkeypatch.setattr(IpcRouterService, "_workspace_form_archive_root", lambda self: archive_root)

    database_url = f"sqlite:///{tmp_path / 'ipc-deploy-new-agent-cycle.db'}"
    macos_workspace = tmp_path / "macos-workspace"
    hr_workspace = tmp_path / "hr-workspace"
    director_workspace = tmp_path / "director-workspace"
    ops_workspace = tmp_path / "ops-workspace"
    _ensure_workspace_dirs(macos_workspace)
    _ensure_workspace_dirs(hr_workspace)
    _ensure_workspace_dirs(director_workspace)
    _ensure_workspace_dirs(ops_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    macos = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Macos_Supervisor",
        status=NodeStatus.ACTIVE,
        workspace_root=str(macos_workspace.resolve()),
    )
    director = repository.create_node(
        node_type=NodeType.AGENT,
        name="Director_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(director_workspace.resolve()),
    )
    hr = repository.create_node(
        node_type=NodeType.AGENT,
        name="HR_Head_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(hr_workspace.resolve()),
    )
    ops = repository.create_node(
        node_type=NodeType.AGENT,
        name="Ops_Head_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(ops_workspace.resolve()),
    )
    repository.link_manager(parent_node_id=macos.id, child_node_id=director.id)
    repository.link_manager(parent_node_id=director.id, child_node_id=hr.id)
    repository.link_manager(parent_node_id=director.id, child_node_id=ops.id)

    client = TestClient(app)
    sync_response = client.post("/v1/forms/workspace/sync", json={"activate": True, "prune_missing": False})
    assert sync_response.status_code == 200
    assert sync_response.json()["summary"]["failed"] == 0
    assert sync_response.json()["summary"]["synced"] == 1

    def assert_skill_manifest(workspace: Path, skill_name: str, expected_description: str) -> None:
        manifest_path = workspace / "skills" / skill_name / "skill.json"
        assert manifest_path.exists()
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert payload["name"] == skill_name
        assert isinstance(payload.get("version"), str) and payload["version"]
        assert payload["description"] == expected_description
        assert isinstance(payload.get("author"), str) and payload["author"]

    def submit_holder_decision(
        *,
        from_file: Path,
        holder_workspace: Path,
        decision: str,
        stale_stage_skill: str,
    ) -> None:
        frontmatter, body = _load_frontmatter(from_file)
        frontmatter["decision"] = decision
        frontmatter["stage_skill"] = stale_stage_skill
        pending_path = holder_workspace / "outbox" / "send" / from_file.name
        pending_path.write_text(
            _render_with_frontmatter(frontmatter=frontmatter, body=body),
            encoding="utf-8",
        )

    request_file = macos_workspace / "outbox" / "send" / "deploy-cycle.md"
    _write_generic_form_file(
        queue_file=request_file,
        form_type="deploy_new_agent",
        stage="BUSINESS_CASE",
        decision="submit_to_hr",
        target="HR_Head_01",
        stage_skill="stale-seed",
        subject="Deploy new agent cycle",
    )

    # BUSINESS_CASE -> HR_REVIEW
    scan_one = client.post("/v1/ipc/actions", json={"action": "scan_forms"})
    assert scan_one.status_code == 200
    item_one = scan_one.json()["items"][0]
    assert item_one["status"] == "routed"
    assert item_one["next_stage"] == "HR_REVIEW"
    hr_delivery = hr_workspace / "inbox" / "new" / "deploy-cycle.md"
    assert hr_delivery.exists()
    hr_frontmatter, _ = _load_frontmatter(hr_delivery)
    assert hr_frontmatter["agent"] == "HR_Head_01"
    assert hr_frontmatter["stage"] == "HR_REVIEW"
    assert hr_frontmatter["stage_skill"] == "review-agent-role-and-template"
    assert hr_frontmatter["target"] == ""
    assert "approve_to_finance: Macos_Supervisor" in hr_frontmatter["target_agent"]
    assert_skill_manifest(
        hr_workspace,
        "review-agent-role-and-template",
        "Perform HR_REVIEW for deploy_new_agent forms and decide whether to move to finance or return for revision.",
    )
    form_id = str(item_one["form_id"])

    # HR_REVIEW -> FINANCE_REVIEW
    submit_holder_decision(
        from_file=hr_delivery,
        holder_workspace=hr_workspace,
        decision="approve_to_finance",
        stale_stage_skill="stale-hr",
    )
    scan_two = client.post("/v1/ipc/actions", json={"action": "scan_forms"})
    assert scan_two.status_code == 200
    macos_delivery = macos_workspace / "inbox" / "new" / "deploy-cycle.md"
    assert macos_delivery.exists()
    macos_frontmatter, _ = _load_frontmatter(macos_delivery)
    assert macos_frontmatter["agent"] == "Macos_Supervisor"
    assert macos_frontmatter["stage"] == "FINANCE_REVIEW"
    assert macos_frontmatter["stage_skill"] == "allocate-agent-budget"
    assert macos_frontmatter["target"] == ""
    assert "approve_to_director: Director_01" in macos_frontmatter["target_agent"]
    assert_skill_manifest(
        macos_workspace,
        "allocate-agent-budget",
        "Perform FINANCE_REVIEW for deploy_new_agent and decide whether budget is approved or returned to HR.",
    )

    # FINANCE_REVIEW -> DIRECTOR_APPROVAL
    submit_holder_decision(
        from_file=macos_delivery,
        holder_workspace=macos_workspace,
        decision="approve_to_director",
        stale_stage_skill="stale-finance",
    )
    scan_three = client.post("/v1/ipc/actions", json={"action": "scan_forms"})
    assert scan_three.status_code == 200
    director_delivery = director_workspace / "inbox" / "new" / "deploy-cycle.md"
    assert director_delivery.exists()
    director_frontmatter, _ = _load_frontmatter(director_delivery)
    assert director_frontmatter["agent"] == "Director_01"
    assert director_frontmatter["stage"] == "DIRECTOR_APPROVAL"
    assert director_frontmatter["stage_skill"] == "final-agent-signoff"
    assert director_frontmatter["target"] == ""
    assert "execute_deployment: Ops_Head_01" in director_frontmatter["target_agent"]
    assert_skill_manifest(
        director_workspace,
        "final-agent-signoff",
        "Execute DIRECTOR_APPROVAL for deploy_new_agent and choose deployment, rework, or rejection.",
    )

    # DIRECTOR_APPROVAL -> AGENT_DEPLOYMENT
    submit_holder_decision(
        from_file=director_delivery,
        holder_workspace=director_workspace,
        decision="execute_deployment",
        stale_stage_skill="stale-director",
    )
    scan_four = client.post("/v1/ipc/actions", json={"action": "scan_forms"})
    assert scan_four.status_code == 200
    ops_delivery = ops_workspace / "inbox" / "new" / "deploy-cycle.md"
    assert ops_delivery.exists()
    ops_frontmatter, _ = _load_frontmatter(ops_delivery)
    assert ops_frontmatter["agent"] == "Ops_Head_01"
    assert ops_frontmatter["stage"] == "AGENT_DEPLOYMENT"
    assert ops_frontmatter["stage_skill"] == "deploy-new-nanobot"
    assert ops_frontmatter["target"] == ""
    assert ops_frontmatter["target_agent"] == ""
    assert_skill_manifest(
        ops_workspace,
        "deploy-new-nanobot",
        (
            "Deploy a repo-local Nanobot agent under workspace/agents/<agent_name>/ with sibling config.json, "
            "workspace scaffold, AGENTS.md instructions, kernel provisioning trigger, and Nanobot smoke commands."
        ),
    )
    for script_name in (
        "deploy_new_nanobot.sh",
        "deploy_new_nanobot_agent.sh",
        "provision_agent_workflow.sh",
    ):
        wrapper_result = subprocess.run(
            [
                "bash",
                str(ops_workspace / "skills" / "deploy-new-nanobot" / "scripts" / script_name),
                "--help",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            env={**os.environ, "OMNICLAW_REPO_ROOT": str(ROOT)},
            check=True,
        )
        assert "Usage:" in wrapper_result.stdout

    # AGENT_DEPLOYMENT -> ARCHIVED (terminal, no holder)
    submit_holder_decision(
        from_file=ops_delivery,
        holder_workspace=ops_workspace,
        decision="deploy_and_archive",
        stale_stage_skill="stale-deploy",
    )
    scan_five = client.post("/v1/ipc/actions", json={"action": "scan_forms"})
    assert scan_five.status_code == 200
    payload_five = scan_five.json()
    assert payload_five["summary"]["routed"] == 1
    archived_item = payload_five["items"][0]
    assert archived_item["delivery_path"] is None
    assert archived_item["next_stage"] == "ARCHIVED"
    archive_frontmatter, _ = _load_frontmatter(Path(archived_item["archive_path"]))
    assert archive_frontmatter["form_id"] == form_id
    assert archive_frontmatter["agent"] == ""
    assert archive_frontmatter["stage"] == "ARCHIVED"
    assert archive_frontmatter["decision"] == ""
    assert archive_frontmatter["stage_skill"] == ""
    assert archive_frontmatter["target"] == ""
    assert archive_frontmatter["target_agent"] == ""

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        form = session.query(FormLedger).filter(FormLedger.form_id == form_id).first()
        assert form is not None
        assert form.current_status == "ARCHIVED"
        assert form.current_holder_node is None
        events = (
            session.query(FormTransitionEvent)
            .filter(FormTransitionEvent.form_id == form_id)
            .order_by(FormTransitionEvent.sequence.asc())
            .all()
        )
        assert [event.to_status for event in events] == [
            "BUSINESS_CASE",
            "HR_REVIEW",
            "FINANCE_REVIEW",
            "DIRECTOR_APPROVAL",
            "AGENT_DEPLOYMENT",
            "ARCHIVED",
        ]


def test_ipc_scan_marks_undelivered_malformed_frontmatter(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'ipc-malformed.db'}"
    worker_workspace = tmp_path / "worker-workspace"
    manager_workspace = tmp_path / "manager-workspace"
    _ensure_workspace_dirs(worker_workspace)
    _ensure_workspace_dirs(manager_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    manager = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Manager_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(manager_workspace.resolve()),
    )
    worker = repository.create_node(
        node_type=NodeType.AGENT,
        name="Worker_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(worker_workspace.resolve()),
    )
    repository.link_manager(parent_node_id=manager.id, child_node_id=worker.id)

    queue_file = worker_workspace / "outbox" / "send" / "bad-message.md"
    _write_message_file(
        queue_file=queue_file,
        sender="Worker_01",
        target="",
        subject=None,
    )

    client = TestClient(app)
    response = client.post("/v1/ipc/actions", json={"action": "scan_messages"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["scanned"] == 1
    assert payload["summary"]["routed"] == 0
    assert payload["summary"]["undelivered"] == 1
    item = payload["items"][0]

    pending = worker_workspace / "outbox" / "send" / "bad-message.md"
    dead_letter = worker_workspace / "outbox" / "dead-letter" / "bad-message.md"
    feedback_sender_inbox = worker_workspace / "inbox" / "new"
    delivered = manager_workspace / "inbox" / "new" / "bad-message.md"
    assert pending.exists() is False
    assert dead_letter.exists()
    assert delivered.exists() is False
    assert item["dead_letter_path"] == str(dead_letter.resolve())
    assert item["feedback_path"] is not None
    assert Path(item["feedback_path"]).exists()
    assert str(Path(item["feedback_path"]).resolve()).startswith(str(feedback_sender_inbox.resolve()))
    assert delivered.exists() is False

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        form = session.query(FormLedger).order_by(FormLedger.created_at.asc()).first()
        assert form is None


def test_ipc_scan_marks_undelivered_when_decision_missing(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'ipc-missing-decision.db'}"
    sender_workspace = tmp_path / "sender-workspace"
    target_workspace = tmp_path / "target-workspace"
    _ensure_workspace_dirs(sender_workspace)
    _ensure_workspace_dirs(target_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    repository.create_node(
        node_type=NodeType.AGENT,
        name="Sender_Decision_Missing",
        status=NodeStatus.ACTIVE,
        workspace_root=str(sender_workspace.resolve()),
    )
    repository.create_node(
        node_type=NodeType.HUMAN,
        name="Target_Decision_Missing",
        status=NodeStatus.ACTIVE,
        workspace_root=str(target_workspace.resolve()),
    )

    queue_file = sender_workspace / "outbox" / "send" / "missing-decision.md"
    _write_message_file(
        queue_file=queue_file,
        sender="Sender_Decision_Missing",
        target="Target_Decision_Missing",
        subject="Missing decision",
        decision=None,
    )

    client = TestClient(app)
    response = client.post("/v1/ipc/actions", json={"action": "scan_messages"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["scanned"] == 1
    assert payload["summary"]["routed"] == 0
    assert payload["summary"]["undelivered"] == 1
    item = payload["items"][0]
    assert "decision is required" in item["failure_reason"]
    assert queue_file.exists() is False
    dead_letter = sender_workspace / "outbox" / "dead-letter" / "missing-decision.md"
    target_feedback = target_workspace / "inbox" / "new"
    assert dead_letter.exists()
    assert item["dead_letter_path"] == str(dead_letter.resolve())
    assert item["feedback_path"] is not None
    assert Path(item["feedback_path"]).exists()
    assert str(Path(item["feedback_path"]).resolve()).startswith(str(target_feedback.resolve()))


def test_ipc_scan_ignores_frontmatter_sender_mismatch(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'ipc-sender-mismatch.db'}"
    worker_workspace = tmp_path / "worker-workspace"
    manager_workspace = tmp_path / "manager-workspace"
    _ensure_workspace_dirs(worker_workspace)
    _ensure_workspace_dirs(manager_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    manager = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Manager_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(manager_workspace.resolve()),
    )
    worker = repository.create_node(
        node_type=NodeType.AGENT,
        name="Worker_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(worker_workspace.resolve()),
    )
    repository.link_manager(parent_node_id=manager.id, child_node_id=worker.id)

    queue_file = worker_workspace / "outbox" / "send" / "wrong-sender.md"
    _write_message_file(
        queue_file=queue_file,
        sender="Other_Node",
        target="Manager_01",
        subject="Hello",
    )

    client = TestClient(app)
    response = client.post("/v1/ipc/actions", json={"action": "scan_messages"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["routed"] == 1
    assert payload["summary"]["undelivered"] == 0

    pending = worker_workspace / "outbox" / "send" / "wrong-sender.md"
    delivered = manager_workspace / "inbox" / "new" / "wrong-sender.md"
    archived = worker_workspace / "outbox" / "archive" / "wrong-sender.md"
    assert pending.exists() is False
    assert delivered.exists()
    assert archived.exists()

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        form = session.query(FormLedger).order_by(FormLedger.created_at.asc()).first()
        assert form is not None
        assert form.sender_node_id == worker.id


def test_ipc_scan_ignores_frontmatter_name_mismatch(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'ipc-name-ignored.db'}"
    worker_workspace = tmp_path / "worker-workspace"
    manager_workspace = tmp_path / "manager-workspace"
    _ensure_workspace_dirs(worker_workspace)
    _ensure_workspace_dirs(manager_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    manager = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Manager_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(manager_workspace.resolve()),
    )
    worker = repository.create_node(
        node_type=NodeType.AGENT,
        name="Worker_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(worker_workspace.resolve()),
    )
    repository.link_manager(parent_node_id=manager.id, child_node_id=worker.id)

    queue_file = worker_workspace / "outbox" / "send" / "name-mismatch.md"
    _write_message_file(
        queue_file=queue_file,
        sender="Worker_01",
        target="Manager_01",
        subject="Name field is optional",
        frontmatter_name="different.md",
    )

    client = TestClient(app)
    response = client.post("/v1/ipc/actions", json={"action": "scan_messages"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["scanned"] == 1
    assert payload["summary"]["routed"] == 1
    assert payload["summary"]["undelivered"] == 0

    delivered = manager_workspace / "inbox" / "new" / "name-mismatch.md"
    archived = worker_workspace / "outbox" / "archive" / "name-mismatch.md"
    assert delivered.exists()
    assert archived.exists()

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        form = session.query(FormLedger).order_by(FormLedger.created_at.asc()).first()
        assert form is not None
        assert form.current_status == FormStatus.WAITING_TO_BE_READ.value
        assert form.message_name == "name-mismatch.md"


def test_ipc_acknowledge_message_read_archives_form(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'ipc-ack-read.db'}"
    sender_workspace = tmp_path / "sender-workspace"
    holder_workspace = tmp_path / "holder-workspace"
    _ensure_workspace_dirs(sender_workspace)
    _ensure_workspace_dirs(holder_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    holder = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Holder_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(holder_workspace.resolve()),
    )
    sender = repository.create_node(
        node_type=NodeType.AGENT,
        name="Sender_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(sender_workspace.resolve()),
    )
    repository.link_manager(parent_node_id=holder.id, child_node_id=sender.id)

    queue_file = sender_workspace / "outbox" / "send" / "read-me.md"
    _write_message_file(
        queue_file=queue_file,
        sender="Sender_01",
        target="Holder_01",
        subject="Please read",
    )

    client = TestClient(app)
    scan_response = client.post("/v1/ipc/actions", json={"action": "scan_messages"})
    assert scan_response.status_code == 200
    form_id = scan_response.json()["items"][0]["form_id"]

    delivered = holder_workspace / "inbox" / "new" / "read-me.md"
    read_copy = holder_workspace / "inbox" / "read" / "read-me.md"
    assert delivered.exists()
    delivered.rename(read_copy)

    ack_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "acknowledge_message_read",
            "form_id": form_id,
            "actor_node_name": "Holder_01",
            "payload": {
                "new_path": str(delivered),
                "read_path": str(read_copy),
            },
        },
    )
    assert ack_response.status_code == 200
    assert ack_response.json()["form"]["current_status"] == FormStatus.ARCHIVED.value
    assert ack_response.json()["form"]["current_holder_node"] is None

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        form = session.query(FormLedger).filter(FormLedger.form_id == form_id).first()
        assert form is not None
        assert form.current_status == FormStatus.ARCHIVED.value
        assert form.current_holder_node is None
        event = (
            session.query(FormTransitionEvent)
            .filter(FormTransitionEvent.form_id == form_id)
            .order_by(FormTransitionEvent.sequence.desc())
            .first()
        )
        assert event is not None
        payload = json.loads(event.payload_json or "{}")
        archive_copy_path = payload.get("master_archive_copy_path")
        assert isinstance(archive_copy_path, str) and archive_copy_path
        assert Path(archive_copy_path).exists()


def test_ipc_scan_supports_terminal_null_stage_without_required_skill(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspace"
    monkeypatch.setattr(FormsService, "_workspace_root", lambda self: workspace_root)
    monkeypatch.setattr(IpcRouterService, "_workspace_forms_root", lambda self: workspace_root / "forms")
    monkeypatch.setattr(IpcRouterService, "_workspace_form_archive_root", lambda self: workspace_root / "form_archive")
    _seed_form_stage_skills(
        workspace_root=workspace_root,
        form_type="custom_message_form",
        skill_names=["draft_internal_message"],
    )

    database_url = f"sqlite:///{tmp_path / 'ipc-terminal-null-no-skill.db'}"
    sender_workspace = tmp_path / "sender-workspace"
    _ensure_workspace_dirs(sender_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    sender = repository.create_node(
        node_type=NodeType.AGENT,
        name="Terminal_Sender_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(sender_workspace.resolve()),
    )

    client = TestClient(app)
    upsert_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "upsert_form_type",
            "type_key": "custom_message_form",
            "version": "3.0.0",
            "workflow_graph": {
                "start_stage": "DRAFT",
                "end_stage": "ARCHIVED",
                "stages": {
                    "DRAFT": {
                        "target": "{{initiator}}",
                        "required_skill": "draft_internal_message",
                        "decisions": {
                            "close": "ARCHIVED",
                        },
                    },
                    "ARCHIVED": {
                        "target": None,
                        "is_terminal": True,
                    },
                },
            },
            "stage_metadata": {},
        },
    )
    assert upsert_response.status_code == 200
    assert upsert_response.json()["validation_errors"] == []

    activate_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "activate_form_type",
            "type_key": "custom_message_form",
            "version": "3.0.0",
        },
    )
    assert activate_response.status_code == 200

    queue_file = sender_workspace / "outbox" / "send" / "terminal-close.md"
    _write_generic_form_file(
        queue_file=queue_file,
        form_type="custom_message_form",
        stage="DRAFT",
        decision="close",
        target=None,
    )

    scan_response = client.post("/v1/ipc/actions", json={"action": "scan_forms"})
    assert scan_response.status_code == 200
    payload = scan_response.json()
    assert payload["summary"]["scanned"] == 1
    assert payload["summary"]["routed"] == 1
    assert payload["summary"]["undelivered"] == 0
    item = payload["items"][0]
    assert item["delivery_path"] is None
    assert item["archive_path"] is not None
    assert item["backup_path"] is not None
    assert queue_file.exists() is False
    archive_frontmatter, _ = _load_frontmatter(Path(item["archive_path"]))
    assert archive_frontmatter["agent"] == ""
    assert archive_frontmatter["stage_skill"] == ""
    assert archive_frontmatter["target"] == ""
    assert archive_frontmatter["target_agent"] == ""

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        form = session.query(FormLedger).filter(FormLedger.form_id == item["form_id"]).first()
        assert form is not None
        assert form.sender_node_id == sender.id
        assert form.current_status == "ARCHIVED"
        assert form.current_holder_node is None


def test_ipc_scan_restores_routed_stage_skill_and_removes_stray_local_skill(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspace"
    monkeypatch.setattr(FormsService, "_workspace_root", lambda self: workspace_root)
    monkeypatch.setattr(IpcRouterService, "_workspace_forms_root", lambda self: workspace_root / "forms")
    monkeypatch.setattr(IpcRouterService, "_workspace_form_archive_root", lambda self: workspace_root / "form_archive")
    _seed_form_stage_skills(
        workspace_root=workspace_root,
        form_type="routed_skill_restore_form",
        skill_names=["draft-internal-message", "read-and-acknowledge-internal-message"],
    )

    database_url = f"sqlite:///{tmp_path / 'ipc-routed-skill-restore.db'}"
    sender_workspace = tmp_path / "sender-workspace"
    target_workspace = tmp_path / "target-workspace"
    _ensure_workspace_dirs(sender_workspace)
    _ensure_workspace_dirs(target_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    repository.create_node(
        node_type=NodeType.AGENT,
        name="Restore_Sender_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(sender_workspace.resolve()),
    )
    repository.create_node(
        node_type=NodeType.AGENT,
        name="Restore_Target_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(target_workspace.resolve()),
    )

    client = TestClient(app)
    upsert_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "upsert_form_type",
            "type_key": "routed_skill_restore_form",
            "version": "1.0.0",
            "workflow_graph": {
                "start_stage": "DRAFT",
                "end_stage": "ARCHIVED",
                "stages": {
                    "DRAFT": {
                        "target": "{{initiator}}",
                        "required_skill": "draft-internal-message",
                        "decisions": {
                            "send": "WAITING_TO_BE_READ",
                        },
                    },
                    "WAITING_TO_BE_READ": {
                        "target": "Restore_Target_01",
                        "required_skill": "read-and-acknowledge-internal-message",
                        "decisions": {
                            "acknowledge_read": "ARCHIVED",
                        },
                    },
                    "ARCHIVED": {
                        "target": None,
                        "is_terminal": True,
                    },
                },
            },
            "stage_metadata": {},
        },
    )
    assert upsert_response.status_code == 200
    assert upsert_response.json()["validation_errors"] == []

    activate_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "activate_form_type",
            "type_key": "routed_skill_restore_form",
            "version": "1.0.0",
        },
    )
    assert activate_response.status_code == 200

    shutil.rmtree(target_workspace / "skills")
    stray_skill_dir = target_workspace / "skills" / "stray-local-skill"
    stray_skill_dir.mkdir(parents=True, exist_ok=True)
    (stray_skill_dir / "SKILL.md").write_text("# stray\n", encoding="utf-8")

    queue_file = sender_workspace / "outbox" / "send" / "restore.md"
    _write_generic_form_file(
        queue_file=queue_file,
        form_type="routed_skill_restore_form",
        stage="DRAFT",
        decision="send",
        target=None,
    )

    scan_response = client.post("/v1/ipc/actions", json={"action": "scan_forms"})
    assert scan_response.status_code == 200
    payload = scan_response.json()
    assert payload["summary"]["routed"] == 1

    restored_skill = target_workspace / "skills" / "read-and-acknowledge-internal-message" / "SKILL.md"
    assert restored_skill.exists()
    assert stray_skill_dir.exists() is False


def test_ipc_scan_stops_processing_after_limit(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'ipc-limit.db'}"
    sender_workspace = tmp_path / "sender-workspace"
    target_workspace = tmp_path / "target-workspace"
    _ensure_workspace_dirs(sender_workspace)
    _ensure_workspace_dirs(target_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    repository.create_node(
        node_type=NodeType.AGENT,
        name="Sender_Limit",
        status=NodeStatus.ACTIVE,
        workspace_root=str(sender_workspace.resolve()),
    )
    repository.create_node(
        node_type=NodeType.HUMAN,
        name="Target_Limit",
        status=NodeStatus.ACTIVE,
        workspace_root=str(target_workspace.resolve()),
    )

    for index in range(15):
        queue_file = sender_workspace / "outbox" / "send" / f"limit-{index}.md"
        _write_message_file(
            queue_file=queue_file,
            sender="Sender_Limit",
            target="Target_Limit",
            subject=f"Message {index}",
        )

    client = TestClient(app)
    response = client.post("/v1/ipc/actions", json={"action": "scan_forms", "limit": 10})
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["scanned"] == 10
    assert payload["summary"]["routed"] == 10
    assert payload["summary"]["undelivered"] == 0
    remaining = sorted((sender_workspace / "outbox" / "send").glob("*.md"))
    assert len(remaining) == 5


def test_ipc_auto_scan_tick_does_not_block_healthz(tmp_path: Path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'ipc-auto-scan-responsiveness.db'}"
    settings = Settings(
        app_name="omniclaw-kernel",
        environment="development",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
        ipc_router_scan_interval_seconds=1,
        ipc_router_auto_scan_enabled=True,
    )

    def _slow_execute(self, request):  # type: ignore[no-untyped-def]
        del self, request
        time.sleep(0.4)
        return {
            "action": "scan_forms",
            "summary": {"scanned": 0, "routed": 0, "undelivered": 0},
            "items": [],
        }

    monkeypatch.setattr(IpcRouterService, "execute", _slow_execute)
    migrate_database_to_head(database_url)
    app = create_app(settings)
    with TestClient(app) as client:
        time.sleep(0.05)
        started = time.monotonic()
        response = client.get("/healthz")
        elapsed = time.monotonic() - started

    assert response.status_code == 200
    assert elapsed < 0.35


def test_ipc_requeue_dead_letter_script_moves_file_to_pending(tmp_path: Path) -> None:
    workspace_root = tmp_path / "worker-workspace"
    _ensure_workspace_dirs(workspace_root)
    dead_letter_file = workspace_root / "outbox" / "dead-letter" / "needs-fix.md"
    dead_letter_file.write_text("---\nform_type: message\n---\n", encoding="utf-8")

    script_path = ROOT / "scripts" / "ipc" / "requeue_dead_letter.sh"
    result = subprocess.run(
        [
            str(script_path),
            "--apply",
            "--workspace-root",
            str(workspace_root),
            "--file",
            "needs-fix.md",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    pending_file = workspace_root / "outbox" / "send" / "needs-fix.md"
    assert pending_file.exists()
    assert dead_letter_file.exists() is False


def test_ipc_blocks_non_allowlisted_initiator_for_new_form(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspace"
    forms_root = workspace_root / "forms" / "restricted_form"
    skills_root = forms_root / "skills"
    skill_dir = skills_root / "draft-restricted"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        (
            "---\n"
            "name: draft-restricted\n"
            "description: Restricted draft skill.\n"
            "---\n\n"
            "# skill\n"
        ),
        encoding="utf-8",
    )

    workflow_payload = {
        "form_type": "restricted_form",
        "version": "1.0.0",
        "description": "Restricted initiator workflow",
        "initiator_allowlist": ["Macos_Supervisor"],
        "start_stage": "DRAFT",
        "end_stage": "ARCHIVED",
        "stages": {
            "DRAFT": {
                "target": "{{initiator}}",
                "required_skill": "draft-restricted",
                "decisions": {"send": "ARCHIVED"},
            },
            "ARCHIVED": {
                "target": None,
                "is_terminal": True,
            },
        },
    }
    forms_root.mkdir(parents=True, exist_ok=True)
    (forms_root / "workflow.json").write_text(json.dumps(workflow_payload, indent=2) + "\n", encoding="utf-8")

    monkeypatch.setattr(FormsService, "_workspace_root", lambda self: workspace_root)
    monkeypatch.setattr(FormsService, "_workspace_forms_root", lambda self: workspace_root / "forms")
    monkeypatch.setattr(IpcRouterService, "_workspace_forms_root", lambda self: workspace_root / "forms")

    database_url = f"sqlite:///{tmp_path / 'ipc-restricted-initiator.db'}"
    macos_workspace = tmp_path / "macos-workspace"
    hr_workspace = tmp_path / "hr-workspace"
    _ensure_workspace_dirs(macos_workspace)
    _ensure_workspace_dirs(hr_workspace)

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    repository.create_node(
        node_type=NodeType.HUMAN,
        name="Macos_Supervisor",
        status=NodeStatus.ACTIVE,
        workspace_root=str(macos_workspace.resolve()),
    )
    repository.create_node(
        node_type=NodeType.AGENT,
        name="HR_Head_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(hr_workspace.resolve()),
    )

    client = TestClient(app)
    sync_response = client.post("/v1/forms/workspace/sync", json={"activate": True, "prune_missing": False})
    assert sync_response.status_code == 200
    assert sync_response.json()["summary"]["failed"] == 0

    request_file = hr_workspace / "outbox" / "send" / "restricted-initiation.md"
    _write_generic_form_file(
        queue_file=request_file,
        form_type="restricted_form",
        stage="DRAFT",
        decision="send",
        target=None,
    )

    scan = client.post("/v1/ipc/actions", json={"action": "scan_forms"})
    assert scan.status_code == 200
    payload = scan.json()
    assert payload["summary"]["undelivered"] == 1
    item = payload["items"][0]
    assert item["status"] == "undelivered"
    assert "not allowed to initiate this form" in str(item["failure_reason"])
