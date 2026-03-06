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


def test_register_human_in_mock_mode_creates_human_node_and_workspace(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'human.db'}"
    workspace_root = tmp_path / "workspace" / "macos"

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
    client = TestClient(app)

    response = client.post(
        "/v1/provisioning/actions",
        json={
            "action": "register_human",
            "username": "macos",
            "node_name": "Macos_Supervisor",
            "workspace_root": str(workspace_root),
            "shell": "/bin/bash",
            "groups": ["sudo"],
            "autonomy_level": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "mock"
    assert payload["node"]["type"] == NodeType.HUMAN.value
    assert payload["node"]["name"] == "Macos_Supervisor"
    assert payload["node"]["linux_username"] == "macos"
    assert payload["node"]["workspace_root"] == str(workspace_root.resolve())
    assert payload["node"]["runtime_config_path"] == "/home/macos/.nanobot/config.json"
    assert payload["line_management"]["subordinate_count"] == 0
    assert payload["line_management"]["has_subordinate"] is False


def test_provision_agent_in_mock_mode_updates_nodes_and_hierarchy(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'provisioning.db'}"
    workspace_root = tmp_path / "workspace" / "agents" / "Director_01" / "workspace"
    expected_config_path = workspace_root.parent / "config.json"

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
        name="Human_Supervisor_01",
        status=NodeStatus.ACTIVE,
    )

    client = TestClient(app)
    response = client.post(
        "/v1/provisioning/actions",
        json={
            "action": "provision_agent",
            "username": "agent_director_01",
            "node_name": "Director_01",
            "shell": "/bin/bash",
            "groups": ["sudo"],
            "workspace": {
                "root": str(workspace_root),
                "scaffold": True,
            },
            "manager_group": "sudo",
            "manager_node_id": manager.id,
            "autonomy_level": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["mode"] == "mock"
    assert "user" not in payload
    assert payload["node"]["name"] == "Director_01"
    assert payload["node"]["status"] == NodeStatus.ACTIVE.value
    assert payload["node"]["autonomy_level"] == 3
    assert payload["node"]["linux_username"] == "agent_director_01"
    assert payload["node"]["workspace_root"] == str(workspace_root.resolve())
    assert payload["node"]["runtime_config_path"] == str(expected_config_path.resolve())
    assert payload["node"]["primary_model"] == "openai-codex/gpt-5.4"
    assert payload["node"]["password_present"] is False
    assert payload["runtime_config"]["path"] == str(expected_config_path.resolve())
    assert payload["runtime_config"]["created"] is True
    assert expected_config_path.exists()
    written_config = json.loads(expected_config_path.read_text(encoding="utf-8"))
    assert written_config["agents"]["defaults"]["workspace"] == str(workspace_root.resolve())

    operations = payload.get("operations", [])
    assert any(operation["step"] == "ensure_workspace" for operation in operations)
    assert all(operation["step"] != "ensure_user" for operation in operations)
    assert all(operation["step"] != "apply_permissions" for operation in operations)

    children = repository.list_children(parent_node_id=manager.id)
    assert len(children) == 1


def test_system_mode_is_blocked_when_privileged_flag_disabled(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'system-blocked.db'}"

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="system",
        allow_privileged_provisioning=False,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    client = TestClient(app)

    response = client.post(
        "/v1/provisioning/actions",
        json={
            "action": "create_linux_user",
            "username": "agent_director_01",
        },
    )

    assert response.status_code == 403
    assert "System provisioning is disabled" in response.json()["detail"]


def test_provision_agent_syncs_model_and_plain_password(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'sync.db'}"
    workspace_root = tmp_path / "workspace" / "agents" / "Director_01" / "workspace"
    config_path = workspace_root.parent / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        (
            "{\n"
            "  \"models\": {\"providers\": {}},\n"
            "  \"agents\": {\"defaults\": {\"model\": {\"primary\": \"openai-codex/gpt-5.3-codex\"}}}\n"
            "}\n"
        ),
        encoding="utf-8",
    )

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
        name="Human_Supervisor_01",
        status=NodeStatus.ACTIVE,
    )
    client = TestClient(app)

    response = client.post(
        "/v1/provisioning/actions",
        json={
            "action": "provision_agent",
            "username": "agent_director_01",
            "node_name": "Director_01",
            "workspace": {
                "root": str(workspace_root),
                "scaffold": True,
            },
            "runtime_config_path": str(config_path),
            "linux_password": "haslo",
            "autonomy_level": 3,
            "manager_node_id": manager.id,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["node"]["primary_model"] == "openai-codex/gpt-5.3-codex"
    assert payload["node"]["password_present"] is True

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        node = (
            session.query(Node)
            .filter(Node.type == NodeType.AGENT, Node.name == "Director_01")
            .order_by(Node.created_at.asc())
            .first()
        )
        assert node is not None
        assert node.primary_model == "openai-codex/gpt-5.3-codex"
        assert node.linux_username == "agent_director_01"
        assert node.workspace_root == str(workspace_root.resolve())
        assert node.runtime_config_path == str(config_path.resolve())
        assert node.linux_password == "haslo"


def test_provision_agent_allows_node_name_without_linux_username(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'node-name-only.db'}"
    workspace_root = tmp_path / "workspace" / "agents" / "Planner_01" / "workspace"

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
        name="Human_Supervisor_01",
        status=NodeStatus.ACTIVE,
    )
    client = TestClient(app)

    response = client.post(
        "/v1/provisioning/actions",
        json={
            "action": "provision_agent",
            "node_name": "Planner_01",
            "manager_node_id": manager.id,
            "workspace": {
                "root": str(workspace_root),
                "scaffold": True,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["node"]["name"] == "Planner_01"
    assert payload["node"]["linux_username"] is None
    assert payload["node"]["workspace_root"] == str(workspace_root.resolve())
    assert payload["node"]["runtime_config_path"] == str((workspace_root.parent / "config.json").resolve())


def test_provision_agent_requires_manager_reference(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'manager-required.db'}"
    workspace_root = tmp_path / "workspace" / "agents" / "Director_01" / "workspace"
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
    client = TestClient(app)

    response = client.post(
        "/v1/provisioning/actions",
        json={
            "action": "provision_agent",
            "username": "agent_director_01",
            "node_name": "Director_01",
            "workspace": {
                "root": str(workspace_root),
                "scaffold": True,
            },
        },
    )
    assert response.status_code == 422
    assert "manager_node_id or manager_node_name is required" in response.json()["detail"]


def test_provision_agent_accepts_agent_manager(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'agent-manager.db'}"
    workspace_root = tmp_path / "workspace" / "agents" / "Worker_01" / "workspace"
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
    manager_agent = repository.create_node(
        node_type=NodeType.AGENT,
        name="Director_01",
        status=NodeStatus.ACTIVE,
    )
    client = TestClient(app)

    response = client.post(
        "/v1/provisioning/actions",
        json={
            "action": "provision_agent",
            "username": "agent_worker_01",
            "node_name": "Worker_01",
            "manager_node_id": manager_agent.id,
            "workspace": {
                "root": str(workspace_root),
                "scaffold": True,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["manager"]["type"] == NodeType.AGENT.value
    assert payload["manager"]["name"] == "Director_01"


def test_provision_agent_rejects_second_manager_for_same_node(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'single-manager.db'}"
    workspace_root = tmp_path / "workspace" / "agents" / "Director_01" / "workspace"
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

    manager_one = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Manager_01",
        status=NodeStatus.ACTIVE,
    )
    manager_two = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Manager_02",
        status=NodeStatus.ACTIVE,
    )

    client = TestClient(app)
    first = client.post(
        "/v1/provisioning/actions",
        json={
            "action": "provision_agent",
            "username": "agent_director_01",
            "node_name": "Director_01",
            "manager_node_id": manager_one.id,
            "workspace": {
                "root": str(workspace_root),
                "scaffold": True,
            },
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/v1/provisioning/actions",
        json={
            "action": "provision_agent",
            "username": "agent_director_01",
            "node_name": "Director_01",
            "manager_node_id": manager_two.id,
            "workspace": {
                "root": str(workspace_root),
                "scaffold": True,
            },
        },
    )
    assert second.status_code == 409
    assert "already has manager" in second.json()["detail"]


def test_set_line_manager_links_existing_agent_node(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'set-manager.db'}"
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
        name="Human_01",
        status=NodeStatus.ACTIVE,
    )
    agent = repository.create_node(
        node_type=NodeType.AGENT,
        name="Director_01",
        status=NodeStatus.ACTIVE,
    )
    client = TestClient(app)

    response = client.post(
        "/v1/provisioning/actions",
        json={
            "action": "set_line_manager",
            "manager_node_id": manager.id,
            "target_node_id": agent.id,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["manager"]["name"] == "Human_01"
    assert payload["target"]["name"] == "Director_01"
    assert payload["manager"]["subordinate_count"] == 1
