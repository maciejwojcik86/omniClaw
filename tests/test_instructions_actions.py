from pathlib import Path
import stat
import sys

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.app import create_app
from omniclaw.config import build_settings
from omniclaw.db.enums import NodeStatus, NodeType
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_session_factory
from tests.helpers import migrate_database_to_head, write_global_company_config


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


def _build_settings_for_workspace(*, tmp_path: Path, workspace_root: Path, database_url: str, access_scope: str):
    global_config_path = tmp_path / ".omniClaw" / "config.json"
    write_global_company_config(
        path=global_config_path,
        workspace_root=workspace_root,
        slug="instructions-test",
        display_name="Instructions Test",
        instructions={"access_scope": access_scope},
        budgeting={
            "daily_company_budget_usd": 3.0,
            "root_allocator_node": "Director_01",
            "reset_time_utc": "00:00",
        },
    )
    workspace_root.mkdir(parents=True, exist_ok=True)
    return build_settings(
        env={
            "OMNICLAW_APP_NAME": "omniclaw-kernel",
            "OMNICLAW_ENV": "test",
            "OMNICLAW_LOG_LEVEL": "INFO",
        },
        company="instructions-test",
        global_config_path=str(global_config_path),
        database_url=database_url,
    )


def _write_unread_form(
    *,
    path: Path,
    sender: str,
    form_type: str,
    stage: str,
    subject: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "---\n"
            f"sender: {sender}\n"
            f"form_type: {form_type}\n"
            f"stage: {stage}\n"
            f"subject: {subject}\n"
            "---\n\n"
            "Body.\n"
        ),
        encoding="utf-8",
    )


def test_instructions_actions_render_templates_and_unread_summary(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'instructions.db'}"
    workspace_root = tmp_path / "workspace"

    human_workspace = workspace_root / "macos"
    director_workspace = workspace_root / "agents" / "Director_01" / "workspace"
    worker_workspace = workspace_root / "agents" / "Worker_01" / "workspace"
    for root in (human_workspace, director_workspace, worker_workspace):
        _ensure_workspace_dirs(root)

    _write_unread_form(
        path=director_workspace / "inbox" / "new" / "status.md",
        sender="Worker_01",
        form_type="message",
        stage="WAITING_TO_BE_READ",
        subject="Daily status",
    )

    settings = _build_settings_for_workspace(
        tmp_path=tmp_path,
        workspace_root=workspace_root,
        database_url=database_url,
        access_scope="descendant",
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))

    human = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Macos_Supervisor",
        status=NodeStatus.ACTIVE,
        workspace_root=str(human_workspace.resolve()),
    )
    director = repository.create_node(
        node_type=NodeType.AGENT,
        name="Director_01",
        status=NodeStatus.ACTIVE,
        role_name="Director",
        workspace_root=str(director_workspace.resolve()),
        runtime_config_path=str((director_workspace.parent / "config.json").resolve()),
        primary_model="openai-codex/gpt-5.4",
    )
    worker = repository.create_node(
        node_type=NodeType.AGENT,
        name="Worker_01",
        status=NodeStatus.ACTIVE,
        role_name="Worker",
        workspace_root=str(worker_workspace.resolve()),
        runtime_config_path=str((worker_workspace.parent / "config.json").resolve()),
        primary_model="openai-codex/gpt-5.4-mini",
    )
    repository.link_manager(parent_node_id=human.id, child_node_id=director.id)
    repository.link_manager(parent_node_id=director.id, child_node_id=worker.id)
    repository.replace_budget_allocations(
        manager_node_id=director.id,
        allocations=[(worker.id, 100.0)],
    )

    client = TestClient(app)

    list_response = client.post(
        "/v1/instructions/actions",
        json={"action": "list_accessible_targets", "actor_node_name": "Macos_Supervisor"},
    )
    assert list_response.status_code == 200
    assert [item["name"] for item in list_response.json()["targets"]] == ["Director_01", "Worker_01"]

    get_response = client.post(
        "/v1/instructions/actions",
        json={
            "action": "get_template",
            "actor_node_name": "Macos_Supervisor",
            "target_node_name": "Director_01",
        },
    )
    assert get_response.status_code == 200
    template_path = Path(get_response.json()["template"]["path"])
    assert template_path == workspace_root / "nanobots_instructions" / "Director_01" / "AGENTS.md"
    assert template_path.exists()

    template_content = (
        "Manager: {{line_manager}}\n"
        "Role: {{node.role_name}}\n"
        "Model: {{node.primary_model}}\n"
        "Budget mode: {{budget.mode}}\n"
        "Daily inflow: {{budget.daily_inflow_usd}}\n"
        "Remaining: {{budget.remaining_usd}}\n"
        "Direct reports:\n{{subordinates_list}}\n"
        "Budget team:\n{{budget.direct_team_summary}}\n"
        "Inbox:\n{{inbox_unread_summary}}\n"
    )
    preview_response = client.post(
        "/v1/instructions/actions",
        json={
            "action": "preview_render",
            "actor_node_name": "Macos_Supervisor",
            "target_node_name": "Director_01",
            "template_content": template_content,
        },
    )
    assert preview_response.status_code == 200
    preview = preview_response.json()["preview"]["rendered_content"]
    assert "Manager: Macos_Supervisor" in preview
    assert "Role: Director" in preview
    assert "Model: openai-codex/gpt-5.4" in preview
    assert "Budget mode: free" in preview
    assert "Daily inflow: 0.00" in preview
    assert "- Worker_01" in preview
    assert "Worker_01 | metered | inflow $3.00 | reserve $0.00 | remaining $3.00" in preview
    assert "- Worker_01 | message | WAITING_TO_BE_READ | Daily status" in preview

    set_response = client.post(
        "/v1/instructions/actions",
        json={
            "action": "set_template",
            "actor_node_name": "Macos_Supervisor",
            "target_node_name": "Director_01",
            "template_content": template_content,
        },
    )
    assert set_response.status_code == 200
    rendered_path = director_workspace / "AGENTS.md"
    rendered_text = rendered_path.read_text(encoding="utf-8")
    assert "Manager: Macos_Supervisor" in rendered_text
    assert "Inbox:" in rendered_text
    assert not (rendered_path.stat().st_mode & stat.S_IWUSR)


def test_instructions_access_scope_and_placeholder_validation(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'instructions-access.db'}"
    workspace_root = tmp_path / "workspace"

    human_workspace = workspace_root / "macos"
    director_workspace = workspace_root / "agents" / "Director_01" / "workspace"
    worker_workspace = workspace_root / "agents" / "Worker_01" / "workspace"
    for root in (human_workspace, director_workspace, worker_workspace):
        _ensure_workspace_dirs(root)

    settings = _build_settings_for_workspace(
        tmp_path=tmp_path,
        workspace_root=workspace_root,
        database_url=database_url,
        access_scope="direct_children",
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))

    human = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Macos_Supervisor",
        status=NodeStatus.ACTIVE,
        workspace_root=str(human_workspace.resolve()),
    )
    director = repository.create_node(
        node_type=NodeType.AGENT,
        name="Director_01",
        status=NodeStatus.ACTIVE,
        role_name="Director",
        workspace_root=str(director_workspace.resolve()),
        runtime_config_path=str((director_workspace.parent / "config.json").resolve()),
    )
    worker = repository.create_node(
        node_type=NodeType.AGENT,
        name="Worker_01",
        status=NodeStatus.ACTIVE,
        role_name="Worker",
        workspace_root=str(worker_workspace.resolve()),
        runtime_config_path=str((worker_workspace.parent / "config.json").resolve()),
    )
    repository.link_manager(parent_node_id=human.id, child_node_id=director.id)
    repository.link_manager(parent_node_id=director.id, child_node_id=worker.id)

    client = TestClient(app)

    forbidden_response = client.post(
        "/v1/instructions/actions",
        json={
            "action": "get_template",
            "actor_node_name": "Macos_Supervisor",
            "target_node_name": "Worker_01",
        },
    )
    assert forbidden_response.status_code == 403

    invalid_response = client.post(
        "/v1/instructions/actions",
        json={
            "action": "set_template",
            "actor_node_name": "Director_01",
            "target_node_name": "Worker_01",
            "template_content": "Bad {{unknown_placeholder}}\n",
        },
    )
    assert invalid_response.status_code == 422
    detail = invalid_response.json()["detail"]
    assert detail["unsupported_placeholders"] == ["unknown_placeholder"]


def test_sync_all_active_agents_installs_manager_skill_for_nodes_with_subordinates(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'instructions-sync.db'}"
    workspace_root = tmp_path / "workspace"

    human_workspace = workspace_root / "macos"
    director_workspace = workspace_root / "agents" / "Director_01" / "workspace"
    worker_workspace = workspace_root / "agents" / "Worker_01" / "workspace"
    for root in (human_workspace, director_workspace, worker_workspace):
        _ensure_workspace_dirs(root)

    settings = _build_settings_for_workspace(
        tmp_path=tmp_path,
        workspace_root=workspace_root,
        database_url=database_url,
        access_scope="descendant",
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))

    human = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Macos_Supervisor",
        status=NodeStatus.ACTIVE,
        workspace_root=str(human_workspace.resolve()),
    )
    director = repository.create_node(
        node_type=NodeType.AGENT,
        name="Director_01",
        status=NodeStatus.ACTIVE,
        role_name="Director",
        workspace_root=str(director_workspace.resolve()),
        runtime_config_path=str((director_workspace.parent / "config.json").resolve()),
    )
    worker = repository.create_node(
        node_type=NodeType.AGENT,
        name="Worker_01",
        status=NodeStatus.ACTIVE,
        role_name="Worker",
        workspace_root=str(worker_workspace.resolve()),
        runtime_config_path=str((worker_workspace.parent / "config.json").resolve()),
    )
    repository.link_manager(parent_node_id=human.id, child_node_id=director.id)
    repository.link_manager(parent_node_id=director.id, child_node_id=worker.id)

    director_stray_skill = director_workspace / "skills" / "stray-local-skill"
    director_stray_skill.mkdir(parents=True, exist_ok=True)
    (director_stray_skill / "SKILL.md").write_text("# stray\n", encoding="utf-8")
    worker_stray_skill = worker_workspace / "skills" / "stray-local-skill"
    worker_stray_skill.mkdir(parents=True, exist_ok=True)
    (worker_stray_skill / "SKILL.md").write_text("# stray\n", encoding="utf-8")

    client = TestClient(app)
    sync_response = client.post(
        "/v1/instructions/actions",
        json={"action": "sync_render", "sync_scope": "all_active_agents"},
    )
    assert sync_response.status_code == 200
    payload = sync_response.json()
    assert payload["summary"]["rendered"] == 2
    assert payload["skill_distribution"]["status"] == "ok"

    director_skill = director_workspace / "skills" / "manage-agent-instructions" / "SKILL.md"
    director_budget_skill = director_workspace / "skills" / "manage-team-budgets" / "SKILL.md"
    worker_skill = worker_workspace / "skills" / "manage-agent-instructions" / "SKILL.md"
    worker_budget_skill = worker_workspace / "skills" / "manage-team-budgets" / "SKILL.md"
    assert director_skill.exists()
    assert director_budget_skill.exists()
    assert director_stray_skill.exists() is False
    assert worker_skill.exists() is False
    assert worker_budget_skill.exists() is False
    assert worker_stray_skill.exists() is False
