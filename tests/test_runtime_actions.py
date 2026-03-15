import json
from decimal import Decimal
from pathlib import Path
import sys

from fastapi.testclient import TestClient
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.app import create_app
from omniclaw.config import Settings
from omniclaw.db.enums import NodeStatus, NodeType
from omniclaw.db.models import AgentLLMCall, Node
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_session_factory
from tests.helpers import migrate_database_to_head


def test_runtime_gateway_lifecycle_in_mock_mode(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    workspace_root = tmp_path / "agent-workspace"
    config_path = tmp_path / "agent-config.json"
    workspace_root.mkdir(parents=True, exist_ok=True)
    config_path.write_text("{\n  \"agents\": {\"defaults\": {\"model\": \"openai-codex/gpt-5.4\"}}\n}\n", encoding="utf-8")

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
        runtime_gateway_command_template="nanobot gateway --workspace {workspace_root} --config {config_path} --port {port}",
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
        runtime_config_path=str(config_path.resolve()),
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
    assert "--workspace" in start_metadata["command"]
    assert str(config_path.resolve()) in start_metadata["command"]

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
    assert listed[0]["type"] == "agent"
    assert listed[0]["role_name"] is None or isinstance(listed[0]["role_name"], str)
    assert "manager_name" in listed[0]
    assert "budget_mode" in listed[0]
    assert "has_virtual_api_key" in listed[0]

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


def test_runtime_invoke_prompt_in_mock_mode(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime-invoke.db'}"
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
        runtime_command_timeout_seconds=10,
        runtime_output_boundary_rel="drafts/runtime",
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="Invoker_01",
        status=NodeStatus.ACTIVE,
        linux_username="invoker_01",
        workspace_root=str(workspace_root.resolve()),
        runtime_config_path=str(config_path.resolve()),
        primary_model="openai-codex/gpt-5.4",
    )
    repository.upsert_budget(
        node_id=node.id,
        virtual_api_key="vk-test",
        daily_limit_usd=2.5,
        current_daily_allowance=2.5,
        current_spend=0.0,
    )
    client = TestClient(app)

    response = client.post(
        "/v1/runtime/actions",
        json={
            "action": "invoke_prompt",
            "node_id": node.id,
            "prompt": "Reply with pong",
            "session_key": "cli:verification-test",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "invoke_prompt"
    assert payload["mode"] == "mock"
    assert payload["invocation"]["status"] == "completed"
    assert payload["invocation"]["session_key"] == "cli:verification-test"
    assert "mock reply" in payload["invocation"]["reply"]
    assert payload["invocation"]["mock_usage"]["total_tokens"] > 0
    assert payload["invocation"]["mock_usage"]["estimated_cost_usd"] > 0
    metadata_path = Path(payload["invocation"]["artifact_paths"]["run_metadata"])
    assert metadata_path.exists()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["action"] == "invoke_prompt"
    assert "nanobot agent" in metadata["command"]

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        calls = session.query(AgentLLMCall).filter(AgentLLMCall.node_id == node.id).all()
        assert len(calls) == 1
        assert calls[0].session_key == "cli:verification-test"

    updated_budget = repository.get_budget(node_id=node.id)
    assert updated_budget is not None
    assert float(updated_budget.current_spend) >= payload["invocation"]["mock_usage"]["estimated_cost_usd"]


def test_runtime_requires_prompt_for_invoke(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime-missing-prompt.db'}"
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
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="Invoker_02",
        status=NodeStatus.ACTIVE,
        linux_username="invoker_02",
        workspace_root=str(workspace_root.resolve()),
        runtime_config_path=str(config_path.resolve()),
    )
    client = TestClient(app)

    response = client.post(
        "/v1/runtime/actions",
        json={"action": "invoke_prompt", "node_id": node.id},
    )
    assert response.status_code == 422
    assert "prompt is required" in response.json()["detail"]


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
        runtime_gateway_command_template="nanobot gateway --workspace {workspace_root} --config {config_path} --port {port}",
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
    config_path = tmp_path / "malicious-config.json"
    workspace_root.mkdir(parents=True, exist_ok=True)
    config_path.write_text("{}", encoding="utf-8")
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
        runtime_config_path=str(config_path.resolve()),
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


def test_runtime_invoke_prompt_system_mode_runs_cli_and_returns_output(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime-system-invoke.db'}"
    workspace_root = tmp_path / "agent-workspace-system"
    config_path = tmp_path / "agent-config-system.json"
    workspace_root.mkdir(parents=True, exist_ok=True)
    config_path.write_text("{}", encoding="utf-8")

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
        runtime_mode="system",
        allow_privileged_runtime=True,
        runtime_use_sudo=False,
        runtime_command_timeout_seconds=10,
        runtime_output_boundary_rel="drafts/runtime",
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="SystemInvoker_01",
        status=NodeStatus.ACTIVE,
        linux_username="system_invoker_01",
        workspace_root=str(workspace_root.resolve()),
        runtime_config_path=str(config_path.resolve()),
    )
    client = TestClient(app)

    class Result:
        returncode = 0
        stdout = "pong from system mode\n"
        stderr = ""

    with patch("omniclaw.runtime.service.subprocess.run", return_value=Result()) as mocked_run:
        response = client.post(
            "/v1/runtime/actions",
            json={
                "action": "invoke_prompt",
                "node_id": node.id,
                "prompt": "Say pong",
                "session_key": "cli:sys",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["invocation"]["reply"] == "pong from system mode"
    called_args = mocked_run.call_args.args[0]
    assert called_args[:2] == ["bash", "-lc"]
    assert "nanobot agent" in called_args[2]
    assert "--session 'cli:sys'" in called_args[2] or '--session cli:sys' in called_args[2]
    called_env = mocked_run.call_args.kwargs["env"]
    pythonpath_parts = called_env["PYTHONPATH"].split(":")
    assert str((ROOT / "src").resolve()) in pythonpath_parts
    assert "/home/macos/nanobot" in pythonpath_parts


def test_runtime_system_mode_budget_report_reconciles_subcent_usage(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime-system-budget.db'}"
    workspace_root = tmp_path / "agent-workspace-budget"
    config_path = tmp_path / "agent-config-budget.json"
    company_config_path = tmp_path / "workspace" / "company_config.json"
    workspace_root.mkdir(parents=True, exist_ok=True)
    company_config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("{}", encoding="utf-8")
    company_config_path.write_text(
        "{\n"
        '  "instructions": {"access_scope": "descendant"},\n'
        '  "budgeting": {"daily_company_budget_usd": 3.0, "root_allocator_node": "Director_01", "reset_time_utc": "00:00"}\n'
        "}\n",
        encoding="utf-8",
    )

    settings = Settings(
        app_name="omniclaw-kernel",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        company_config_path=str(company_config_path.resolve()),
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
        runtime_mode="system",
        allow_privileged_runtime=True,
        runtime_use_sudo=False,
        runtime_command_timeout_seconds=10,
        runtime_output_boundary_rel="drafts/runtime",
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))
    director = repository.create_node(
        node_type=NodeType.AGENT,
        name="Director_01",
        status=NodeStatus.ACTIVE,
        linux_username="director_01",
        workspace_root=str((tmp_path / "director-workspace").resolve()),
        runtime_config_path=str((tmp_path / "director-config.json").resolve()),
    )
    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="SystemBudget_01",
        status=NodeStatus.ACTIVE,
        linux_username="system_budget_01",
        workspace_root=str(workspace_root.resolve()),
        runtime_config_path=str(config_path.resolve()),
    )
    repository.link_manager(parent_node_id=director.id, child_node_id=node.id)
    repository.replace_budget_allocations(manager_node_id=director.id, allocations=[(node.id, 100.0)])
    repository.upsert_budget(
        node_id=node.id,
        virtual_api_key="vk-budget",
        budget_mode="metered",
        daily_limit_usd=Decimal("3.000000"),
        current_daily_allowance=Decimal("3.000000"),
        current_spend=Decimal("0.000000"),
        parent_node_id=director.id,
    )
    client = TestClient(app)

    class Result:
        returncode = 0
        stdout = "paid response\n"
        stderr = ""

    with patch("omniclaw.runtime.service.subprocess.run", return_value=Result()):
        repository.insert_agent_llm_call(
            node_id=node.id,
            session_key="cli:sys-budget",
            model="openrouter/test-paid-model",
            provider="CustomProvider",
            prompt_tokens=100,
            completion_tokens=10,
            total_tokens=110,
            estimated_cost_usd=Decimal("0.000995"),
        )
        response = client.post(
            "/v1/budgets/actions",
            json={"action": "budget_report"},
        )

    assert response.status_code == 200
    payload = response.json()
    rows = {row["node"]["name"]: row for row in payload["rows"]}
    assert rows["SystemBudget_01"]["current_spend"] == 0.000995
    assert payload["company_budget"]["current_total_spend_usd"] == 0.000995


def test_runtime_rejects_invalid_gateway_command_template(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime-invalid-template.db'}"
    workspace_root = tmp_path / "agent-workspace-template"
    config_path = tmp_path / "template-config.json"
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
        runtime_gateway_command_template="nanobot gateway --workspace {workspace_root} --config {bad_key}",
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
        runtime_config_path=str(config_path.resolve()),
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
    config_path = tmp_path / "boundary-config.json"
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
        runtime_gateway_command_template="nanobot gateway --workspace {workspace_root} --config {config_path} --port {port}",
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
        runtime_config_path=str(config_path.resolve()),
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
