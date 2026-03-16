import json
from pathlib import Path
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


def _write_skill_dir(path: Path, *, name: str, description: str = "Test skill", version: str = "1.0.0") -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        (
            "---\n"
            f"name: {name}\n"
            f"description: {description}\n"
            f"version: \"{version}\"\n"
            "author: test-suite\n"
            "---\n\n"
            f"# {name}\n"
        ),
        encoding="utf-8",
    )


def _build_settings_for_workspace(*, tmp_path: Path, workspace_root: Path, database_url: str):
    global_config_path = tmp_path / ".omniClaw" / "config.json"
    write_global_company_config(
        path=global_config_path,
        workspace_root=workspace_root,
        slug="skills-test",
        display_name="Skills Test",
        instructions={"access_scope": "descendant"},
        skills={"default_agent_skill_names": []},
    )
    workspace_root.mkdir(parents=True, exist_ok=True)
    return build_settings(
        env={
            "OMNICLAW_APP_NAME": "omniclaw-kernel",
            "OMNICLAW_ENV": "test",
            "OMNICLAW_LOG_LEVEL": "INFO",
        },
        company="skills-test",
        global_config_path=str(global_config_path),
        database_url=database_url,
    )


def test_skills_actions_draft_activate_assign_remove_and_sync_workspace(tmp_path: Path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'skills-actions.db'}"
    workspace_root = tmp_path / "workspace"

    monkeypatch.setattr("omniclaw.skills.service._repo_root", lambda: tmp_path)

    settings = _build_settings_for_workspace(
        tmp_path=tmp_path,
        workspace_root=workspace_root,
        database_url=database_url,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))

    agent_workspace = tmp_path / "agents" / "Worker_01" / "workspace"
    agent_workspace.mkdir(parents=True, exist_ok=True)
    stray_skill_dir = agent_workspace / "skills" / "stray-skill"
    stray_skill_dir.mkdir(parents=True, exist_ok=True)
    (stray_skill_dir / "SKILL.md").write_text("# stray\n", encoding="utf-8")

    agent = repository.create_node(
        node_type=NodeType.AGENT,
        name="Worker_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(agent_workspace.resolve()),
    )

    draft_source = tmp_path / "drafts" / "loose-skill-a"
    _write_skill_dir(draft_source, name="loose-skill-a", description="Loose skill A")

    client = TestClient(app)

    draft_response = client.post(
        "/v1/skills/actions",
        json={
            "action": "draft_master_skill",
            "skill_name": "loose-skill-a",
            "source_path": str(draft_source.resolve()),
        },
    )
    assert draft_response.status_code == 200
    assert draft_response.json()["skill"]["lifecycle_status"] == "DRAFT"
    copied_skill_dir = workspace_root / "master_skills" / "loose-skill-a"
    assert (copied_skill_dir / "SKILL.md").exists()

    activate_response = client.post(
        "/v1/skills/actions",
        json={
            "action": "set_master_skill_status",
            "skill_name": "loose-skill-a",
            "lifecycle_status": "ACTIVE",
        },
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["skill"]["lifecycle_status"] == "ACTIVE"

    assign_response = client.post(
        "/v1/skills/actions",
        json={
            "action": "assign_master_skills",
            "target_node_id": agent.id,
            "skill_names": ["loose-skill-a"],
        },
    )
    assert assign_response.status_code == 200
    payload = assign_response.json()
    assert payload["sync"]["status"] == "synced"
    assert (agent_workspace / "skills" / "loose-skill-a" / "SKILL.md").exists()
    assert (agent_workspace / "skills" / "stray-skill").exists() is False

    list_response = client.post(
        "/v1/skills/actions",
        json={
            "action": "list_agent_skill_assignments",
            "target_node_id": agent.id,
        },
    )
    assert list_response.status_code == 200
    assignments = list_response.json()["assignments"]
    assert len(assignments) == 1
    assert assignments[0]["name"] == "loose-skill-a"
    assert assignments[0]["assignment_sources"] == ["MANUAL"]

    remove_response = client.post(
        "/v1/skills/actions",
        json={
            "action": "remove_master_skills",
            "target_node_id": agent.id,
            "skill_names": ["loose-skill-a"],
        },
    )
    assert remove_response.status_code == 200
    assert remove_response.json()["sync"]["status"] == "synced"
    assert (agent_workspace / "skills" / "loose-skill-a").exists() is False


def test_skills_actions_manager_scope_enforces_descendant_access(tmp_path: Path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'skills-scope.db'}"
    workspace_root = tmp_path / "workspace"
    monkeypatch.setattr("omniclaw.skills.service._repo_root", lambda: tmp_path)

    _write_skill_dir(workspace_root / "master_skills" / "scoped-skill", name="scoped-skill")

    settings = _build_settings_for_workspace(
        tmp_path=tmp_path,
        workspace_root=workspace_root,
        database_url=database_url,
    )
    migrate_database_to_head(database_url)
    app = create_app(settings)
    repository = KernelRepository(create_session_factory(database_url))

    manager = repository.create_node(
        node_type=NodeType.AGENT,
        name="Manager_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str((tmp_path / "agents" / "Manager_01" / "workspace").resolve()),
    )
    child = repository.create_node(
        node_type=NodeType.AGENT,
        name="Child_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str((tmp_path / "agents" / "Child_01" / "workspace").resolve()),
    )
    outsider = repository.create_node(
        node_type=NodeType.AGENT,
        name="Outsider_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str((tmp_path / "agents" / "Outsider_01" / "workspace").resolve()),
    )
    repository.link_manager(parent_node_id=manager.id, child_node_id=child.id)

    client = TestClient(app)
    allowed = client.post(
        "/v1/skills/actions",
        json={
            "action": "assign_master_skills",
            "actor_node_id": manager.id,
            "target_node_id": child.id,
            "skill_names": ["scoped-skill"],
        },
    )
    assert allowed.status_code == 200

    denied = client.post(
        "/v1/skills/actions",
        json={
            "action": "assign_master_skills",
            "actor_node_id": manager.id,
            "target_node_id": outsider.id,
            "skill_names": ["scoped-skill"],
        },
    )
    assert denied.status_code == 403
