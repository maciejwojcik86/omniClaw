import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.app import create_app
from omniclaw.config import Settings
from omniclaw.db.enums import NodeStatus, NodeType
from omniclaw.db.models import Node
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_session_factory
from tests.helpers import migrate_database_to_head


def test_runtime_gateway_lifecycle_in_mock_mode(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    workspace_root = tmp_path / "agent-workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

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
        runtime_gateway_command_template="nullclaw gateway --host {host} --port {port}",
        runtime_command_timeout_seconds=10,
        runtime_output_boundary_rel="drafts/runtime",
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="Director_01",
        status=NodeStatus.ACTIVE,
        linux_uid=1001,
        linux_username="agent_director_01",
        workspace_root=str(workspace_root.resolve()),
        nullclaw_config_path="/home/agent_director_01/.nullclaw/config.json",
        primary_model="openai-codex/gpt-5.3-codex",
    )

    client = TestClient(app)
    start_response = client.post(
        "/v1/runtime/actions",
        json={
            "action": "gateway_start",
            "node_id": node.id,
            "gateway_host": "127.0.0.1",
            "gateway_port": 3000,
        },
    )
    assert start_response.status_code == 200
    start_payload = start_response.json()
    assert start_payload["mode"] == "mock"
    assert start_payload["gateway"]["status"] in {"started", "already_running"}
    assert start_payload["node"]["gateway_running"] is True
    assert start_payload["node"]["gateway_started_at"] is not None
    start_metadata_path = Path(start_payload["gateway"]["artifact_paths"]["run_metadata"])
    assert start_metadata_path.exists()
    start_metadata = json.loads(start_metadata_path.read_text(encoding="utf-8"))
    assert start_metadata["action"] == "gateway_start"
    assert start_metadata["exit_code"] in {0, 10}
    assert start_metadata["artifact_paths"]["output_root"].startswith(str(workspace_root.resolve()))

    status_response = client.post(
        "/v1/runtime/actions",
        json={
            "action": "gateway_status",
            "node_name": "Director_01",
        },
    )
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["gateway"]["running"] is True

    stop_response = client.post(
        "/v1/runtime/actions",
        json={
            "action": "gateway_stop",
            "node_name": "Director_01",
        },
    )
    assert stop_response.status_code == 200
    stop_payload = stop_response.json()
    assert stop_payload["gateway"]["running"] is False
    assert stop_payload["node"]["gateway_running"] is False
    assert stop_payload["node"]["gateway_stopped_at"] is not None
    stop_metadata_path = Path(stop_payload["gateway"]["artifact_paths"]["run_metadata"])
    assert stop_metadata_path.exists()
    stop_metadata = json.loads(stop_metadata_path.read_text(encoding="utf-8"))
    assert stop_metadata["action"] == "gateway_stop"
    assert stop_metadata["artifact_paths"]["output_root"].startswith(str(workspace_root.resolve()))

    list_response = client.post(
        "/v1/runtime/actions",
        json={"action": "list_agents"},
    )
    assert list_response.status_code == 200
    listed = list_response.json()["agents"]
    assert len(listed) == 1
    assert listed[0]["name"] == "Director_01"
    assert listed[0]["deployed"] is True

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        refreshed = (
            session.query(Node)
            .filter(Node.type == NodeType.AGENT, Node.id == node.id)
            .order_by(Node.created_at.asc())
            .first()
        )
        assert refreshed is not None
        assert refreshed.gateway_running is False
        assert refreshed.gateway_stopped_at is not None


def test_runtime_requires_node_identifier(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime-missing-node.db'}"
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
        runtime_gateway_command_template="nullclaw gateway --host {host} --port {port}",
        runtime_command_timeout_seconds=10,
        runtime_output_boundary_rel="drafts/runtime",
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    client = TestClient(app)

    response = client.post(
        "/v1/runtime/actions",
        json={"action": "gateway_start"},
    )
    assert response.status_code == 422
    assert "node_id or node_name is required" in response.json()["detail"]


def test_runtime_rejects_malicious_gateway_host(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime-malicious-host.db'}"
    workspace_root = tmp_path / "agent-workspace-malicious"
    workspace_root.mkdir(parents=True, exist_ok=True)
    migrate_database_to_head(database_url)

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
    )
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="Malicious_Host_Node",
        status=NodeStatus.ACTIVE,
        linux_username="malicious_host_node",
        workspace_root=str(workspace_root.resolve()),
        nullclaw_config_path="/home/malicious_host_node/.nullclaw/config.json",
    )
    client = TestClient(app)

    response = client.post(
        "/v1/runtime/actions",
        json={
            "action": "gateway_start",
            "node_id": node.id,
            "gateway_host": "127.0.0.1;touch /tmp/pwned",
        },
    )
    assert response.status_code == 422
    assert "gateway_host" in str(response.json())
    assert (Path("/tmp/pwned")).exists() is False


def test_runtime_rejects_invalid_gateway_command_template(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime-invalid-template.db'}"
    workspace_root = tmp_path / "agent-workspace-template"
    workspace_root.mkdir(parents=True, exist_ok=True)

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
        runtime_gateway_command_template="nullclaw gateway --host {bad_key}",
        runtime_command_timeout_seconds=10,
        runtime_output_boundary_rel="drafts/runtime",
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="Template_Bad",
        status=NodeStatus.ACTIVE,
        linux_username="template_bad",
        workspace_root=str(workspace_root.resolve()),
        nullclaw_config_path="/home/template_bad/.nullclaw/config.json",
    )
    client = TestClient(app)

    response = client.post(
        "/v1/runtime/actions",
        json={
            "action": "gateway_start",
            "node_id": node.id,
        },
    )
    assert response.status_code == 500
    assert "Invalid runtime gateway command template" in response.json()["detail"]


def test_runtime_rejects_output_boundary_escape(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime-boundary-escape.db'}"
    workspace_root = tmp_path / "agent-workspace-boundary"
    workspace_root.mkdir(parents=True, exist_ok=True)

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
        runtime_gateway_command_template="nullclaw gateway --host {host} --port {port}",
        runtime_command_timeout_seconds=10,
        runtime_output_boundary_rel="../escape",
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="Boundary_Bad",
        status=NodeStatus.ACTIVE,
        linux_username="boundary_bad",
        workspace_root=str(workspace_root.resolve()),
        nullclaw_config_path="/home/boundary_bad/.nullclaw/config.json",
    )
    client = TestClient(app)

    response = client.post(
        "/v1/runtime/actions",
        json={
            "action": "gateway_start",
            "node_id": node.id,
        },
    )
    assert response.status_code == 500
    assert "runtime output boundary escapes workspace" in response.json()["detail"]
