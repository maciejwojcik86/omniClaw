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
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_session_factory


def test_provision_agent_in_mock_mode_updates_nodes_and_hierarchy(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'provisioning.db'}"

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
    )
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
                "root": "/home/agent_director_01/workspace",
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
    assert payload["user"]["username"] == "agent_director_01"
    assert payload["user"]["created"] is True
    assert payload["user"]["uid"] is not None
    assert payload["node"]["name"] == "Director_01"
    assert payload["node"]["status"] == NodeStatus.ACTIVE.value
    assert payload["node"]["autonomy_level"] == 3

    operations = payload.get("operations", [])
    assert any(operation["step"] == "ensure_user" for operation in operations)
    assert any(operation["step"] == "ensure_workspace" for operation in operations)
    assert any(operation["step"] == "apply_permissions" for operation in operations)

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
