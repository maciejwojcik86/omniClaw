from pathlib import Path
import sys
import time
import json
import stat
import subprocess

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
from omniclaw.ipc.service import IpcRouterService
from tests.helpers import migrate_database_to_head


def _ensure_workspace_dirs(workspace_root: Path) -> None:
    for relative in (
        "inbox/unread",
        "inbox/read",
        "outbox/pending",
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
    if target is not None:
        frontmatter.append(f"target: {target}")
    if subject is not None:
        frontmatter.append(f"subject: {subject}")
    frontmatter.append("---")
    payload = "\n".join(frontmatter) + "\n\nHello from OmniClaw.\n"
    queue_file.write_text(payload, encoding="utf-8")


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

    queue_file = worker_workspace / "outbox" / "pending" / "status-update.md"
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

    delivered = manager_workspace / "inbox" / "unread" / "status-update.md"
    archived = worker_workspace / "outbox" / "archive" / "status-update.md"
    assert delivered.exists()
    assert archived.exists()
    assert queue_file.exists() is False
    assert bool(delivered.stat().st_mode & stat.S_IWGRP)
    assert bool(archived.stat().st_mode & stat.S_IWGRP)
    delivered_text = delivered.read_text(encoding="utf-8")
    assert "decision:" in delivered_text
    assert "transition:" not in delivered_text
    assert "initiator_node_id:" not in delivered_text
    assert "target_node_id:" not in delivered_text
    assert "in_reply_to:" not in delivered_text

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        form = session.query(FormLedger).order_by(FormLedger.created_at.asc()).first()
        assert form is not None
        assert form.type == "message"
        assert form.form_type_key == "message"
        assert form.current_status == FormStatus.WAITING_TO_BE_READ.value
        assert form.sender_node_id == worker.id
        assert form.target_node_id == manager.id
        assert form.subject == "Daily status"
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

    queue_file = sender_workspace / "outbox" / "pending" / "request.md"
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
    delivered = target_workspace / "inbox" / "unread" / "request.md"
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

    queue_file = sender_workspace / "outbox" / "pending" / "legacy-frontmatter.md"
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

    delivered = target_workspace / "inbox" / "unread" / "legacy-frontmatter.md"
    assert delivered.exists()
    delivered_text = delivered.read_text(encoding="utf-8")
    assert "decision:" in delivered_text
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

    queue_file = sender_workspace / "outbox" / "pending" / "custom-message.md"
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

    delivered = target_workspace / "inbox" / "unread" / "custom-message.md"
    read_copy = target_workspace / "inbox" / "read" / "custom-message.md"
    assert delivered.exists()
    delivered.rename(read_copy)

    ack_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "transition_form",
            "form_id": form_id,
            "actor_node_id": target.id,
            "decision_key": "mark_read",
            "payload": {
                "unread_path": str(delivered),
                "read_path": str(read_copy),
            },
        },
    )
    assert ack_response.status_code == 200
    assert ack_response.json()["form"]["current_status"] == "READ_ARCHIVED"
    assert ack_response.json()["form"]["current_holder_node"] is None


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

    queue_file = worker_workspace / "outbox" / "pending" / "bad-message.md"
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

    pending = worker_workspace / "outbox" / "pending" / "bad-message.md"
    dead_letter = worker_workspace / "outbox" / "dead-letter" / "bad-message.md"
    feedback_sender_inbox = worker_workspace / "inbox" / "unread"
    delivered = manager_workspace / "inbox" / "unread" / "bad-message.md"
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

    queue_file = sender_workspace / "outbox" / "pending" / "missing-decision.md"
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
    target_feedback = target_workspace / "inbox" / "unread"
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

    queue_file = worker_workspace / "outbox" / "pending" / "wrong-sender.md"
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

    pending = worker_workspace / "outbox" / "pending" / "wrong-sender.md"
    delivered = manager_workspace / "inbox" / "unread" / "wrong-sender.md"
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

    queue_file = worker_workspace / "outbox" / "pending" / "name-mismatch.md"
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

    delivered = manager_workspace / "inbox" / "unread" / "name-mismatch.md"
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

    queue_file = sender_workspace / "outbox" / "pending" / "read-me.md"
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

    delivered = holder_workspace / "inbox" / "unread" / "read-me.md"
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
                "unread_path": str(delivered),
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

    queue_file = sender_workspace / "outbox" / "pending" / "terminal-close.md"
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

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        form = session.query(FormLedger).filter(FormLedger.form_id == item["form_id"]).first()
        assert form is not None
        assert form.sender_node_id == sender.id
        assert form.current_status == "ARCHIVED"
        assert form.current_holder_node is None


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
        queue_file = sender_workspace / "outbox" / "pending" / f"limit-{index}.md"
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
    remaining = sorted((sender_workspace / "outbox" / "pending").glob("*.md"))
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
    pending_file = workspace_root / "outbox" / "pending" / "needs-fix.md"
    assert pending_file.exists()
    assert dead_letter_file.exists() is False
