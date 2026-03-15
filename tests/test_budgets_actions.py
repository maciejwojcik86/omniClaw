from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import httpx
import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.app import create_app
from omniclaw.budgets.engine import BudgetEngine
from omniclaw.config import Settings
from omniclaw.db.enums import BudgetMode, NodeStatus, NodeType
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_session_factory
from tests.helpers import migrate_database_to_head


def _write_company_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "{\n"
        '  "instructions": {\n'
        '    "access_scope": "descendant"\n'
        "  },\n"
        '  "budgeting": {\n'
        '    "daily_company_budget_usd": 4.0,\n'
        '    "root_allocator_node": "Director_01",\n'
        '    "reset_time_utc": "00:00"\n'
        "  }\n"
        "}\n",
        encoding="utf-8",
    )


def _ensure_workspace_dirs(workspace_root: Path) -> None:
    for relative in (
        "inbox/new",
        "inbox/read",
        "outbox/send",
        "outbox/archive",
        "outbox/dead-letter",
        "outbox/drafts",
        "skills",
    ):
        (workspace_root / relative).mkdir(parents=True, exist_ok=True)


@pytest.fixture
def app_and_client(tmp_path: Path):
    database_url = f"sqlite:///{tmp_path / 'budgets.db'}"
    company_config_path = tmp_path / "workspace" / "company_config.json"
    _write_company_config(company_config_path)

    settings = Settings(
        app_name="omniclaw-kernel-budgets",
        environment="test",
        log_level="INFO",
        database_url=database_url,
        provisioning_mode="mock",
        allow_privileged_provisioning=False,
        company_config_path=str(company_config_path.resolve()),
        litellm_proxy_url="http://localhost:4000",
        litellm_master_key="sk-master-key",
    )
    migrate_database_to_head(database_url)

    with patch("omniclaw.app.load_settings") as mock_load_settings:
        mock_load_settings.return_value = settings
        with patch("omniclaw.budgets.service.load_settings") as mock_budget_settings:
            mock_budget_settings.return_value = settings
            app = create_app(settings)
            repository = KernelRepository(create_session_factory(database_url))
            yield app, TestClient(app), repository, settings, tmp_path


def _create_agent(
    repository: KernelRepository,
    *,
    name: str,
    workspace_root: Path,
    role_name: str = "Worker",
) -> object:
    _ensure_workspace_dirs(workspace_root)
    return repository.create_node(
        node_type=NodeType.AGENT,
        name=name,
        status=NodeStatus.ACTIVE,
        role_name=role_name,
        workspace_root=str(workspace_root.resolve()),
        runtime_config_path=str((workspace_root.parent / "config.json").resolve()),
    )


@patch("omniclaw.budgets.service.LiteLLMClient")
def test_sync_node_cost_preserves_kernel_limit(mock_client_class, app_and_client) -> None:
    _app, client, repository, _settings, tmp_path = app_and_client

    mock_instance = AsyncMock()
    mock_instance.get_user_info.return_value = {"spend": 1.25, "max_budget": 7.5}
    mock_client_class.return_value = mock_instance

    node = _create_agent(
        repository,
        name="BudgetAgent_01",
        workspace_root=tmp_path / "workspace" / "agents" / "BudgetAgent_01" / "workspace",
    )
    repository.upsert_budget(
        node_id=node.id,
        virtual_api_key="sk-virtual-test",
        budget_mode=BudgetMode.METERED,
        daily_limit_usd=Decimal("5.00"),
        current_daily_allowance=Decimal("5.00"),
    )

    response = client.post(
        "/v1/budgets/actions",
        json={"action": "sync_node_cost", "node_id": node.id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["budget"]["current_spend"] == 1.25
    assert payload["budget"]["daily_limit_usd"] == 5.0
    assert payload["provider_max_budget_usd"] == 7.5


def test_team_budget_view_returns_manager_and_direct_reports(app_and_client) -> None:
    _app, client, repository, _settings, tmp_path = app_and_client

    director = _create_agent(
        repository,
        name="Director_01",
        role_name="Director",
        workspace_root=tmp_path / "workspace" / "agents" / "Director_01" / "workspace",
    )
    hr = _create_agent(
        repository,
        name="HR_Head_01",
        role_name="HR Head",
        workspace_root=tmp_path / "workspace" / "agents" / "HR_Head_01" / "workspace",
    )
    ops = _create_agent(
        repository,
        name="Ops_Head_01",
        role_name="Ops Head",
        workspace_root=tmp_path / "workspace" / "agents" / "Ops_Head_01" / "workspace",
    )
    repository.link_manager(parent_node_id=director.id, child_node_id=hr.id)
    repository.link_manager(parent_node_id=director.id, child_node_id=ops.id)
    repository.replace_budget_allocations(
        manager_node_id=director.id,
        allocations=[(hr.id, 25.0), (ops.id, 50.0)],
    )

    response = client.post(
        "/v1/budgets/actions",
        json={"action": "team_budget_view", "actor_node_name": "Director_01"},
    )

    assert response.status_code == 200
    payload = response.json()
    rows = {row["node"]["name"]: row for row in payload["rows"]}
    assert set(rows) == {"Director_01", "HR_Head_01", "Ops_Head_01"}
    assert rows["Director_01"]["budget_mode"] == "free"
    assert rows["Director_01"]["daily_inflow_usd"] == 1.0
    assert rows["HR_Head_01"]["daily_inflow_usd"] == 1.0
    assert rows["Ops_Head_01"]["daily_inflow_usd"] == 2.0


def test_due_cycle_date_handles_utc_reset_time_without_type_error(app_and_client, monkeypatch) -> None:
    _app, _client, repository, settings, _tmp_path = app_and_client
    engine = BudgetEngine(repository=repository, settings=settings)

    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz == timezone.utc
            return cls(2026, 3, 8, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("omniclaw.budgets.engine.datetime", _FrozenDateTime)

    assert engine.due_cycle_date() == date(2026, 3, 8)


def test_set_team_allocations_recalculates_descendants_and_writes_notifications(app_and_client) -> None:
    _app, client, repository, _settings, tmp_path = app_and_client

    director = _create_agent(
        repository,
        name="Director_01",
        role_name="Director",
        workspace_root=tmp_path / "workspace" / "agents" / "Director_01" / "workspace",
    )
    ops = _create_agent(
        repository,
        name="Ops_Head_01",
        role_name="Ops Head",
        workspace_root=tmp_path / "workspace" / "agents" / "Ops_Head_01" / "workspace",
    )
    worker = _create_agent(
        repository,
        name="Worker_01",
        role_name="Worker",
        workspace_root=tmp_path / "workspace" / "agents" / "Worker_01" / "workspace",
    )
    analyst = _create_agent(
        repository,
        name="Analyst_01",
        role_name="Analyst",
        workspace_root=tmp_path / "workspace" / "agents" / "Analyst_01" / "workspace",
    )
    repository.link_manager(parent_node_id=director.id, child_node_id=ops.id)
    repository.link_manager(parent_node_id=director.id, child_node_id=worker.id)
    repository.link_manager(parent_node_id=ops.id, child_node_id=analyst.id)
    repository.replace_budget_allocations(
        manager_node_id=ops.id,
        allocations=[(analyst.id, 50.0)],
    )

    response = client.post(
        "/v1/budgets/actions",
        json={
            "action": "set_team_allocations",
            "actor_node_name": "Director_01",
            "allocations": [
                {"child_node_name": "Ops_Head_01", "percentage": 50.0},
                {"child_node_name": "Worker_01", "percentage": 25.0},
            ],
            "reason": "Shift more budget to operations",
            "impact_summary": "Ops keeps more reserve and Worker_01 runs leaner today.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    notifications = {item["node"]: item for item in payload["notifications"]}
    assert set(notifications) == {"Ops_Head_01", "Worker_01"}
    assert notifications["Ops_Head_01"]["review_required"] is True
    assert notifications["Worker_01"]["review_required"] is False

    ops_budget = repository.get_budget(node_id=ops.id)
    worker_budget = repository.get_budget(node_id=worker.id)
    analyst_budget = repository.get_budget(node_id=analyst.id)
    assert float(ops_budget.current_daily_allowance) == 1.0
    assert float(worker_budget.current_daily_allowance) == 1.0
    assert float(analyst_budget.current_daily_allowance) == 1.0
    assert ops_budget.review_required_at is not None

    notification_path = Path(notifications["Ops_Head_01"]["path"])
    assert notification_path.exists()
    assert "Shift more budget to operations" in notification_path.read_text(encoding="utf-8")


def test_set_team_allocations_accepts_legacy_alias_fields(app_and_client) -> None:
    _app, client, repository, _settings, tmp_path = app_and_client

    director = _create_agent(
        repository,
        name="Director_01",
        role_name="Director",
        workspace_root=tmp_path / "workspace" / "agents" / "Director_01" / "workspace",
    )
    hr = _create_agent(
        repository,
        name="HR_Head_01",
        role_name="HR Head",
        workspace_root=tmp_path / "workspace" / "agents" / "HR_Head_01" / "workspace",
    )
    ops = _create_agent(
        repository,
        name="Ops_Head_01",
        role_name="Ops Head",
        workspace_root=tmp_path / "workspace" / "agents" / "Ops_Head_01" / "workspace",
    )
    repository.link_manager(parent_node_id=director.id, child_node_id=hr.id)
    repository.link_manager(parent_node_id=director.id, child_node_id=ops.id)

    response = client.post(
        "/v1/budgets/actions",
        json={
            "action": "set_team_allocations",
            "actor_node_name": "Director_01",
            "allocations": [
                {"agent_name": "HR_Head_01", "share_percent": 30.0},
                {"node_id": ops.id, "share_percent": 40.0},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    allocations = {item["child_node_id"]: item["percentage"] for item in payload["allocations"]}
    assert allocations == {
        hr.id: 30.0,
        ops.id: 40.0,
    }


@patch("omniclaw.budgets.service.LiteLLMClient")
def test_set_team_allocations_records_sync_errors_without_blocking_update(mock_client_class, app_and_client) -> None:
    _app, client, repository, _settings, tmp_path = app_and_client

    request = httpx.Request("POST", "http://localhost:4000/user/update")
    response = httpx.Response(status_code=400, request=request)

    mock_instance = AsyncMock()
    mock_instance.update_user_budget.side_effect = httpx.HTTPStatusError(
        "Client error '400 Bad Request' for url 'http://localhost:4000/user/update'",
        request=request,
        response=response,
    )
    mock_client_class.return_value = mock_instance

    director = _create_agent(
        repository,
        name="Director_01",
        role_name="Director",
        workspace_root=tmp_path / "workspace" / "agents" / "Director_01" / "workspace",
    )
    worker = _create_agent(
        repository,
        name="Worker_01",
        workspace_root=tmp_path / "workspace" / "agents" / "Worker_01" / "workspace",
    )
    repository.link_manager(parent_node_id=director.id, child_node_id=worker.id)
    repository.upsert_budget(
        node_id=worker.id,
        virtual_api_key="sk-worker",
        budget_mode=BudgetMode.METERED,
    )

    response = client.post(
        "/v1/budgets/actions",
        json={
            "action": "set_team_allocations",
            "actor_node_name": "Director_01",
            "allocations": [
                {"child_node_name": "Worker_01", "percentage": 100.0},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["synced_caps"] == 0
    assert payload["sync_errors"][0]["node_name"] == "Worker_01"

    allocation_rows = repository.list_budget_allocations(manager_node_id=director.id)
    assert len(allocation_rows) == 1
    assert float(allocation_rows[0].percentage) == 100.0


@patch("omniclaw.budgets.service.LiteLLMClient")
def test_update_node_allowance_requires_break_glass_for_managed_node(mock_client_class, app_and_client) -> None:
    _app, client, repository, _settings, tmp_path = app_and_client

    mock_instance = AsyncMock()
    mock_instance.update_user_budget.return_value = {"max_budget": 15.0}
    mock_client_class.return_value = mock_instance

    director = _create_agent(
        repository,
        name="Director_01",
        role_name="Director",
        workspace_root=tmp_path / "workspace" / "agents" / "Director_01" / "workspace",
    )
    worker = _create_agent(
        repository,
        name="Worker_01",
        workspace_root=tmp_path / "workspace" / "agents" / "Worker_01" / "workspace",
    )
    repository.link_manager(parent_node_id=director.id, child_node_id=worker.id)
    repository.upsert_budget(
        node_id=worker.id,
        virtual_api_key="sk-update",
        parent_node_id=director.id,
    )

    response = client.post(
        "/v1/budgets/actions",
        json={
            "action": "update_node_allowance",
            "node_name": "Worker_01",
            "new_daily_limit_usd": 15.0,
        },
    )

    assert response.status_code == 409
    assert "hierarchy-managed" in response.json()["detail"]


def test_budget_report_returns_company_and_per_node_summary(app_and_client) -> None:
    _app, client, repository, _settings, tmp_path = app_and_client

    director = _create_agent(
        repository,
        name="Director_01",
        role_name="Director",
        workspace_root=tmp_path / "workspace" / "agents" / "Director_01" / "workspace",
    )
    worker = _create_agent(
        repository,
        name="Worker_01",
        workspace_root=tmp_path / "workspace" / "agents" / "Worker_01" / "workspace",
    )
    repository.link_manager(parent_node_id=director.id, child_node_id=worker.id)
    repository.replace_budget_allocations(
        manager_node_id=director.id,
        allocations=[(worker.id, 100.0)],
    )
    repository.upsert_budget(
        node_id=worker.id,
        virtual_api_key="sk-worker",
        budget_mode=BudgetMode.METERED,
        daily_limit_usd=Decimal("3.00"),
        current_daily_allowance=Decimal("3.00"),
        current_spend=Decimal("1.25"),
        parent_node_id=director.id,
    )
    repository.insert_agent_llm_call(
        node_id=worker.id,
        session_key="cli:budget-report-manual",
        model="openrouter/test-paid-model",
        provider="CustomProvider",
        total_tokens=100,
        estimated_cost_usd=Decimal("1.25"),
    )

    response = client.post("/v1/budgets/actions", json={"action": "budget_report"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "budget_report"
    assert payload["company_budget"]["daily_company_budget_usd"] == 4.0
    rows = {row["node"]["name"]: row for row in payload["rows"]}
    assert "Worker_01" in rows
    assert rows["Worker_01"]["manager_name"] == "Director_01"
    assert rows["Worker_01"]["budget_mode"] == "metered"
    assert rows["Worker_01"]["current_spend"] == 1.25
    assert rows["Worker_01"]["remaining_budget_usd"] == pytest.approx(
        rows["Worker_01"]["available_budget_usd"] - rows["Worker_01"]["current_spend"]
    )
    assert rows["Worker_01"]["has_virtual_api_key"] is True
    assert payload["allocations"][0]["manager_name"] == "Director_01"
    assert payload["allocations"][0]["child_node_name"] == "Worker_01"


def test_budget_report_reconciles_subcent_usage_costs_into_budget_spend(app_and_client) -> None:
    _app, client, repository, _settings, tmp_path = app_and_client

    director = _create_agent(
        repository,
        name="Director_01",
        role_name="Director",
        workspace_root=tmp_path / "workspace" / "agents" / "Director_01" / "workspace",
    )
    worker = _create_agent(
        repository,
        name="Worker_01",
        workspace_root=tmp_path / "workspace" / "agents" / "Worker_01" / "workspace",
    )
    repository.link_manager(parent_node_id=director.id, child_node_id=worker.id)
    repository.replace_budget_allocations(
        manager_node_id=director.id,
        allocations=[(worker.id, 100.0)],
    )
    repository.upsert_budget(
        node_id=worker.id,
        virtual_api_key="sk-worker",
        budget_mode=BudgetMode.METERED,
        daily_limit_usd=Decimal("3.000000"),
        current_daily_allowance=Decimal("3.000000"),
        current_spend=Decimal("0.000000"),
        parent_node_id=director.id,
    )
    repository.insert_agent_llm_call(
        node_id=worker.id,
        session_key="cli:subcent",
        model="openrouter/test-paid-model",
        provider="CustomProvider",
        total_tokens=3881,
        estimated_cost_usd=Decimal("0.000995"),
    )

    response = client.post("/v1/budgets/actions", json={"action": "budget_report"})

    assert response.status_code == 200
    payload = response.json()
    rows = {row["node"]["name"]: row for row in payload["rows"]}
    assert rows["Worker_01"]["current_spend"] == 0.000995
    assert rows["Worker_01"]["remaining_budget_usd"] == pytest.approx(
        rows["Worker_01"]["available_budget_usd"] - rows["Worker_01"]["current_spend"]
    )
    assert payload["company_budget"]["current_total_spend_usd"] == 0.000995
    persisted = repository.get_budget(node_id=worker.id)
    assert persisted is not None
    assert persisted.current_spend == Decimal("0.000995")


def test_run_budget_cycle_resets_spend_and_rolls_reserve(app_and_client) -> None:
    _app, client, repository, _settings, tmp_path = app_and_client

    director = _create_agent(
        repository,
        name="Director_01",
        role_name="Director",
        workspace_root=tmp_path / "workspace" / "agents" / "Director_01" / "workspace",
    )
    worker = _create_agent(
        repository,
        name="Worker_01",
        workspace_root=tmp_path / "workspace" / "agents" / "Worker_01" / "workspace",
    )
    repository.link_manager(parent_node_id=director.id, child_node_id=worker.id)
    repository.replace_budget_allocations(
        manager_node_id=director.id,
        allocations=[(worker.id, 100.0)],
    )
    repository.upsert_budget(
        node_id=worker.id,
        budget_mode=BudgetMode.METERED,
        daily_limit_usd=Decimal("3.00"),
        current_daily_allowance=Decimal("3.00"),
        current_spend=Decimal("1.25"),
    )
    response = client.post(
        "/v1/budgets/actions",
        json={"action": "run_budget_cycle"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"

    updated_budget = repository.get_budget(node_id=worker.id)
    assert float(updated_budget.current_spend) == 0.0
    assert float(updated_budget.rollover_reserve_usd) == 1.75
    assert float(updated_budget.current_daily_allowance) == 4.0
    assert float(updated_budget.daily_limit_usd) == 5.75
    assert repository.get_budget_cycle(cycle_date=datetime.now(timezone.utc).date()) is not None
