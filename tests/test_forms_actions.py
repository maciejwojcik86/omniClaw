import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.app import create_app
from omniclaw.config import Settings
from omniclaw.db.enums import NodeSkillAssignmentSource, NodeStatus, NodeType
from omniclaw.db.models import FormTransitionEvent
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_session_factory
from omniclaw.forms.service import FormsService
from tests.helpers import migrate_database_to_head


def test_forms_actions_support_registry_and_branching_transition(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'forms-actions.db'}"

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
    )
    coder = repository.create_node(
        node_type=NodeType.AGENT,
        name="Coder_01",
        status=NodeStatus.ACTIVE,
    )
    reviewer = repository.create_node(
        node_type=NodeType.AGENT,
        name="Reviewer_01",
        status=NodeStatus.ACTIVE,
    )

    client = TestClient(app)

    upsert_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "upsert_form_type",
            "type_key": "feature_pipeline_form",
            "version": "1.0.0",
            "workflow_graph": {
                "initial_status": "DRAFT",
                "edges": [
                    {
                        "from": "DRAFT",
                        "to": "PLANNED",
                        "decision": "submit",
                        "next_holder": {"strategy": "field_ref", "value": "implementer_node_id"},
                    },
                    {
                        "from": "PLANNED",
                        "to": "IMPLEMENTED_TESTED",
                        "decision": "implemented",
                        "next_holder": {"strategy": "field_ref", "value": "reviewer_node_id"},
                    },
                    {
                        "from": "IMPLEMENTED_TESTED",
                        "to": "CHANGES_REQUESTED",
                        "decision": "request_changes",
                        "next_holder": {"strategy": "field_ref", "value": "implementer_node_id"},
                    },
                    {
                        "from": "IMPLEMENTED_TESTED",
                        "to": "APPROVED",
                        "decision": "approve",
                        "next_holder": {"strategy": "field_ref", "value": "manager_node_id"},
                    },
                ],
            },
            "stage_metadata": {
                "DRAFT": {
                    "stage_skill_ref": ".codex/skills/form-type-authoring/SKILL.md",
                    "stage_template_ref": "templates/forms/feature_pipeline_form/draft.md",
                },
                "PLANNED": {
                    "stage_skill_ref": ".codex/skills/form-stage-execution/SKILL.md",
                    "stage_template_ref": "templates/forms/feature_pipeline_form/planned.md",
                },
                "IMPLEMENTED_TESTED": {
                    "stage_skill_ref": ".codex/skills/form-stage-execution/SKILL.md",
                    "stage_template_ref": "templates/forms/feature_pipeline_form/implemented_tested.md",
                },
                "CHANGES_REQUESTED": {
                    "stage_skill_ref": ".codex/skills/form-stage-execution/SKILL.md",
                    "stage_template_ref": "templates/forms/feature_pipeline_form/changes_requested.md",
                },
                "APPROVED": {
                    "stage_skill_ref": ".codex/skills/form-stage-execution/SKILL.md",
                    "stage_template_ref": "templates/forms/feature_pipeline_form/approved.md",
                },
            },
        },
    )
    assert upsert_response.status_code == 200
    payload = upsert_response.json()
    assert payload["validation_errors"] == []

    activate_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "activate_form_type",
            "type_key": "feature_pipeline_form",
            "version": "1.0.0",
        },
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["form_type"]["lifecycle_state"] == "ACTIVE"

    create_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "create_form",
            "type_key": "feature_pipeline_form",
            "form_id_hint": "feature-login-flow",
            "initial_holder_node_id": manager.id,
            "actor_node_id": manager.id,
        },
    )
    assert create_response.status_code == 200
    created_form = create_response.json()["form"]
    assert created_form["current_status"] == "DRAFT"
    assert created_form["current_holder_node"] == manager.id

    form_id = created_form["form_id"]

    transition_one = client.post(
        "/v1/forms/actions",
        json={
            "action": "transition_form",
            "form_id": form_id,
            "decision_key": "submit",
            "actor_node_id": manager.id,
            "context": {
                "implementer_node_id": coder.id,
                "reviewer_node_id": reviewer.id,
                "manager_node_id": manager.id,
            },
        },
    )
    assert transition_one.status_code == 200
    assert transition_one.json()["form"]["current_status"] == "PLANNED"
    assert transition_one.json()["form"]["current_holder_node"] == coder.id

    transition_two = client.post(
        "/v1/forms/actions",
        json={
            "action": "transition_form",
            "form_id": form_id,
            "decision_key": "implemented",
            "actor_node_id": coder.id,
            "context": {
                "implementer_node_id": coder.id,
                "reviewer_node_id": reviewer.id,
                "manager_node_id": manager.id,
            },
        },
    )
    assert transition_two.status_code == 200
    assert transition_two.json()["form"]["current_status"] == "IMPLEMENTED_TESTED"
    assert transition_two.json()["form"]["current_holder_node"] == reviewer.id

    transition_three = client.post(
        "/v1/forms/actions",
        json={
            "action": "transition_form",
            "form_id": form_id,
            "decision_key": "request_changes",
            "actor_node_id": reviewer.id,
            "context": {
                "implementer_node_id": coder.id,
                "reviewer_node_id": reviewer.id,
                "manager_node_id": manager.id,
            },
        },
    )
    assert transition_three.status_code == 200
    assert transition_three.json()["form"]["current_status"] == "CHANGES_REQUESTED"
    assert transition_three.json()["form"]["current_holder_node"] == coder.id

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        events = (
            session.query(FormTransitionEvent)
            .filter(FormTransitionEvent.form_id == form_id)
            .order_by(FormTransitionEvent.sequence.asc())
            .all()
        )
        assert len(events) == 4
        assert [event.to_status for event in events] == [
            "DRAFT",
            "PLANNED",
            "IMPLEMENTED_TESTED",
            "CHANGES_REQUESTED",
        ]


def test_forms_workspace_sync_endpoint_loads_master_workflows_into_db(tmp_path: Path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'forms-sync.db'}"

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
    hr_workspace = tmp_path / "hr-workspace"
    hr_workspace.mkdir(parents=True, exist_ok=True)
    repository.create_node(
        node_type=NodeType.HUMAN,
        name="Department_Head_HR",
        status=NodeStatus.ACTIVE,
        workspace_root=str(hr_workspace),
    )

    forms_root = tmp_path / "workspace-forms"
    form_type_dir = forms_root / "deploy_new_agent"
    (form_type_dir / "skills" / "draft-agent-business-case").mkdir(parents=True, exist_ok=True)
    (form_type_dir / "skills" / "review-agent-role-and-template").mkdir(parents=True, exist_ok=True)
    (form_type_dir / "skills" / "archive-agent-deployment-form").mkdir(parents=True, exist_ok=True)
    (form_type_dir / "skills" / "draft-agent-business-case" / "SKILL.md").write_text(
        (
            "---\n"
            "name: draft-agent-business-case\n"
            "description: Draft BUSINESS_CASE details for deployment request.\n"
            "---\n\n"
            "# skill\n"
        ),
        encoding="utf-8",
    )
    (form_type_dir / "skills" / "review-agent-role-and-template" / "SKILL.md").write_text(
        (
            "---\n"
            "name: review-agent-role-and-template\n"
            "description: Review role definition and validate template completeness.\n"
            "---\n\n"
            "# skill\n"
        ),
        encoding="utf-8",
    )
    (form_type_dir / "skills" / "archive-agent-deployment-form" / "SKILL.md").write_text(
        (
            "---\n"
            "name: archive-agent-deployment-form\n"
            "description: Final archive handling for deployment forms.\n"
            "---\n\n"
            "# skill\n"
        ),
        encoding="utf-8",
    )
    (form_type_dir / "workflow.json").write_text(
        json.dumps(
            {
                "form_type": "deploy_new_agent",
                "version": "2.0.0",
                "description": "Deployment workflow",
                "start_stage": "BUSINESS_CASE",
                "end_stage": "ARCHIVED",
                "stages": {
                    "BUSINESS_CASE": {
                        "target": "{{initiator}}",
                        "required_skill": "draft-agent-business-case",
                        "decisions": {"submit_to_hr": "HR_REVIEW"},
                    },
                    "HR_REVIEW": {
                        "target": "Department_Head_HR",
                        "required_skill": "review-agent-role-and-template",
                        "decisions": {"approve_to_archive": "ARCHIVED"},
                    },
                    "ARCHIVED": {
                        "is_terminal": True,
                        "target": "none",
                        "required_skill": "archive-agent-deployment-form",
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(FormsService, "_workspace_forms_root", lambda self: forms_root)
    client = TestClient(app)
    response = client.post("/v1/forms/workspace/sync", json={"activate": True, "prune_missing": False})
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["scanned"] == 1
    assert payload["summary"]["synced"] == 1
    assert payload["summary"]["failed"] == 0
    assert payload["summary"]["created"] == 1
    assert payload["summary"]["activated"] == 1

    definition = repository.get_form_type_definition(type_key="deploy_new_agent", active_only=True)
    assert definition is not None
    assert definition.version == "2.0.0"

    distributed_manifest = (
        hr_workspace
        / "skills"
        / "review-agent-role-and-template"
        / "skill.json"
    )
    assert distributed_manifest.exists()
    payload = json.loads(distributed_manifest.read_text(encoding="utf-8"))
    assert payload["name"] == "review-agent-role-and-template"
    assert isinstance(payload.get("version"), str) and payload["version"]
    assert payload["description"] == "Review role definition and validate template completeness."
    assert isinstance(payload.get("author"), str) and payload["author"]

    master_skills = repository.list_master_skills(form_type_key="deploy_new_agent")
    assert master_skills
    review_skill = next((item for item in master_skills if item.name == "review-agent-role-and-template"), None)
    assert review_skill is not None
    assert review_skill.form_type_key == "deploy_new_agent"
    assert review_skill.description == "Review role definition and validate template completeness."
    assert review_skill.master_path.endswith("/deploy_new_agent/skills/review-agent-role-and-template")


def test_forms_workspace_sync_endpoint_rejects_invalid_master_workflow(tmp_path: Path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'forms-sync-invalid.db'}"

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

    forms_root = tmp_path / "workspace-forms"
    form_type_dir = forms_root / "broken_form"
    form_type_dir.mkdir(parents=True, exist_ok=True)
    (form_type_dir / "workflow.json").write_text(
        json.dumps(
            {
                "form_type": "broken_form",
                "version": "1.0.0",
                "start_stage": "DRAFT",
                "end_stage": "ARCHIVED",
                "stages": {
                    "DRAFT": {
                        "target": "Missing_HR_Node",
                        "required_skill": "missing_skill",
                        "decisions": {"submit": "ARCHIVED"},
                    },
                    "ARCHIVED": {
                        "is_terminal": True,
                        "target": "none",
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(FormsService, "_workspace_forms_root", lambda self: forms_root)
    client = TestClient(app)
    response = client.post("/v1/forms/workspace/sync", json={"activate": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["scanned"] == 1
    assert payload["summary"]["failed"] == 1
    assert payload["summary"]["synced"] == 0
    assert payload["items"][0]["status"] == "failed"
    assert repository.get_form_type_definition(type_key="broken_form") is None


def test_forms_actions_rejects_non_snake_case_type_key(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'forms-invalid.db'}"

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
        "/v1/forms/actions",
        json={
            "action": "upsert_form_type",
            "type_key": "FeaturePipeline",
            "version": "1.0.0",
            "workflow_graph": {
                "initial_status": "DRAFT",
                "edges": [
                    {
                        "from": "DRAFT",
                        "to": "DONE",
                        "decision": "submit",
                        "next_holder": {"strategy": "static_node", "value": "node-1"},
                    }
                ],
            },
            "stage_metadata": {
                "DRAFT": {
                    "stage_skill_ref": ".codex/skills/form-type-authoring/SKILL.md",
                    "stage_template_ref": "templates/forms/example/draft.md",
                },
                "DONE": {
                    "stage_skill_ref": ".codex/skills/form-stage-execution/SKILL.md",
                    "stage_template_ref": "templates/forms/example/done.md",
                },
            },
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "snake_case" in str(detail)


def test_forms_actions_requires_end_node_in_node_graph(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'forms-missing-end-node.db'}"
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

    upsert_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "upsert_form_type",
            "type_key": "broken_form",
            "version": "1.0.0",
            "workflow_graph": {
                "start_node": "draft",
                "nodes": {
                    "draft": {
                        "status": "DRAFT",
                        "stage_skill_ref": ".codex/skills/form-stage-execution/SKILL.md",
                        "holder": {"strategy": "previous_actor"},
                    },
                    "done": {
                        "status": "DONE",
                        "stage_skill_ref": ".codex/skills/form-stage-execution/SKILL.md",
                        "holder": {"strategy": "none"},
                    },
                },
                "edges": [
                    {
                        "from": "draft",
                        "to": "done",
                        "decision": "finish",
                    }
                ],
            },
            "stage_metadata": {},
        },
    )
    assert upsert_response.status_code == 200
    assert "workflow_graph.end_node is required" in upsert_response.json()["validation_errors"]

    activate_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "activate_form_type",
            "type_key": "broken_form",
            "version": "1.0.0",
        },
    )
    assert activate_response.status_code == 400
    assert "workflow_graph.end_node is required" in str(activate_response.json()["detail"])


def test_forms_actions_supports_static_node_name_and_terminal_none_holder(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'forms-static-name.db'}"
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

    requester = repository.create_node(
        node_type=NodeType.AGENT,
        name="Requester_01",
        status=NodeStatus.ACTIVE,
    )
    approver = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Budget_Approver",
        status=NodeStatus.ACTIVE,
    )

    client = TestClient(app)
    upsert_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "upsert_form_type",
            "type_key": "budget_request_form",
            "version": "1.0.0",
            "workflow_graph": {
                "initial_status": "SUBMITTED",
                "edges": [
                    {
                        "from": "SUBMITTED",
                        "to": "IN_REVIEW",
                        "decision": "route_to_approver",
                        "next_holder": {"strategy": "static_node_name", "value": "Budget_Approver"},
                    },
                    {
                        "from": "IN_REVIEW",
                        "to": "ARCHIVED",
                        "decision": "approve",
                        "next_holder": {"strategy": "none"},
                    },
                ],
            },
            "stage_metadata": {
                "SUBMITTED": {
                    "stage_skill_ref": ".codex/skills/form-stage-execution/SKILL.md",
                    "stage_template_ref": "templates/forms/feature_pipeline_form/draft.md",
                },
                "IN_REVIEW": {
                    "stage_skill_ref": ".codex/skills/form-stage-execution/SKILL.md",
                    "stage_template_ref": "templates/forms/feature_pipeline_form/implemented_tested.md",
                },
                "ARCHIVED": {
                    "stage_skill_ref": ".codex/skills/form-stage-execution/SKILL.md",
                    "stage_template_ref": "templates/forms/feature_pipeline_form/approved.md",
                },
            },
        },
    )
    assert upsert_response.status_code == 200
    assert upsert_response.json()["validation_errors"] == []

    activate_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "activate_form_type",
            "type_key": "budget_request_form",
            "version": "1.0.0",
        },
    )
    assert activate_response.status_code == 200

    create_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "create_form",
            "type_key": "budget_request_form",
            "initial_holder_node_id": requester.id,
            "actor_node_id": requester.id,
            "form_id_hint": "budget-request-001",
        },
    )
    assert create_response.status_code == 200
    form_id = create_response.json()["form"]["form_id"]

    route_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "transition_form",
            "form_id": form_id,
            "decision_key": "route_to_approver",
            "actor_node_id": requester.id,
        },
    )
    assert route_response.status_code == 200
    assert route_response.json()["form"]["current_status"] == "IN_REVIEW"
    assert route_response.json()["form"]["current_holder_node"] == approver.id

    approve_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "transition_form",
            "form_id": form_id,
            "decision_key": "approve",
            "actor_node_id": approver.id,
        },
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["form"]["current_status"] == "ARCHIVED"
    assert approve_response.json()["form"]["current_holder_node"] is None


def test_forms_actions_supports_deployment_request_reject_loop_and_terminal_approval(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'forms-deployment-request.db'}"
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

    requester = repository.create_node(
        node_type=NodeType.AGENT,
        name="Director_01",
        status=NodeStatus.ACTIVE,
    )
    supervisor = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Macos_Supervisor",
        status=NodeStatus.ACTIVE,
    )

    client = TestClient(app)

    upsert_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "upsert_form_type",
            "type_key": "nanobot_agent_deployment_request_form",
            "version": "1.0.0",
            "workflow_graph": {
                "start_node": "request_draft",
                "end_node": "approved_for_deployment",
                "nodes": {
                    "request_draft": {
                        "status": "REQUEST_DRAFT",
                        "stage_skill_ref": ".codex/skills/request-nanobot-agent-deployment/SKILL.md",
                        "holder": {"strategy": "field_ref", "value": "requester_node_id"},
                    },
                    "waiting_human_approval": {
                        "status": "WAITING_HUMAN_APPROVAL",
                        "stage_skill_ref": ".codex/skills/review-nanobot-agent-deployment-request/SKILL.md",
                        "holder": {"strategy": "static_node_name", "value": "Macos_Supervisor"},
                    },
                    "approved_for_deployment": {
                        "status": "APPROVED_FOR_DEPLOYMENT",
                        "stage_skill_ref": ".codex/skills/deploy-new-nanobot/SKILL.md",
                        "holder": {"strategy": "none"},
                    },
                },
                "edges": [
                    {
                        "from": "request_draft",
                        "to": "waiting_human_approval",
                        "decision": "submit_for_review",
                    },
                    {
                        "from": "waiting_human_approval",
                        "to": "request_draft",
                        "decision": "reject_with_feedback",
                    },
                    {
                        "from": "waiting_human_approval",
                        "to": "approved_for_deployment",
                        "decision": "approve_deployment",
                    },
                ],
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
            "type_key": "nanobot_agent_deployment_request_form",
            "version": "1.0.0",
        },
    )
    assert activate_response.status_code == 200

    create_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "create_form",
            "type_key": "nanobot_agent_deployment_request_form",
            "initial_holder_node_id": requester.id,
            "actor_node_id": requester.id,
            "form_id_hint": "deploy-agent-assistant",
        },
    )
    assert create_response.status_code == 200
    form_id = create_response.json()["form"]["form_id"]
    assert create_response.json()["form"]["current_status"] == "REQUEST_DRAFT"
    assert create_response.json()["form"]["current_holder_node"] == requester.id

    submit_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "transition_form",
            "form_id": form_id,
            "decision_key": "submit_for_review",
            "actor_node_id": requester.id,
            "context": {
                "requester_node_id": requester.id,
            },
        },
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["form"]["current_status"] == "WAITING_HUMAN_APPROVAL"
    assert submit_response.json()["form"]["current_holder_node"] == supervisor.id

    reject_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "transition_form",
            "form_id": form_id,
            "decision_key": "reject_with_feedback",
            "actor_node_id": supervisor.id,
            "context": {
                "requester_node_id": requester.id,
            },
            "payload": {
                "decision_note": "Role scope too broad; narrow to runtime-gateway operations first.",
            },
        },
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["form"]["current_status"] == "REQUEST_DRAFT"
    assert reject_response.json()["form"]["current_holder_node"] == requester.id

    resubmit_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "transition_form",
            "form_id": form_id,
            "decision_key": "submit_for_review",
            "actor_node_id": requester.id,
            "context": {
                "requester_node_id": requester.id,
            },
        },
    )
    assert resubmit_response.status_code == 200
    assert resubmit_response.json()["form"]["current_status"] == "WAITING_HUMAN_APPROVAL"
    assert resubmit_response.json()["form"]["current_holder_node"] == supervisor.id

    approve_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "transition_form",
            "form_id": form_id,
            "decision_key": "approve_deployment",
            "actor_node_id": supervisor.id,
            "payload": {
                "decision_note": "Approved for deployment within Director_01 team budget.",
            },
        },
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["form"]["current_status"] == "APPROVED_FOR_DEPLOYMENT"
    assert approve_response.json()["form"]["current_holder_node"] is None

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        events = (
            session.query(FormTransitionEvent)
            .filter(FormTransitionEvent.form_id == form_id)
            .order_by(FormTransitionEvent.sequence.asc())
            .all()
        )
        assert [event.to_status for event in events] == [
            "REQUEST_DRAFT",
            "WAITING_HUMAN_APPROVAL",
            "REQUEST_DRAFT",
            "WAITING_HUMAN_APPROVAL",
            "APPROVED_FOR_DEPLOYMENT",
        ]


def test_forms_actions_allows_terminal_null_target_without_required_skill(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspace"
    monkeypatch.setattr(FormsService, "_workspace_root", lambda self: workspace_root)
    _seed_stage_skills(
        workspace_root=workspace_root,
        type_key="custom_message_form",
        skill_names=["draft-internal-message"],
    )

    database_url = f"sqlite:///{tmp_path / 'forms-terminal-null-no-skill.db'}"
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

    requester = repository.create_node(
        node_type=NodeType.AGENT,
        name="Requester_01",
        status=NodeStatus.ACTIVE,
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
                        "required_skill": "draft-internal-message",
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
    payload = upsert_response.json()
    assert payload["validation_errors"] == []
    draft_stage = payload["form_type"]["workflow_graph"]["stages"]["DRAFT"]
    assert draft_stage["decisions"]["close"] == "ARCHIVED"
    assert "transitions" not in draft_stage

    activate_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "activate_form_type",
            "type_key": "custom_message_form",
            "version": "3.0.0",
        },
    )
    assert activate_response.status_code == 200

    create_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "create_form",
            "type_key": "custom_message_form",
            "initial_holder_node_id": requester.id,
            "actor_node_id": requester.id,
            "form_id_hint": "terminal-null-no-skill",
        },
    )
    assert create_response.status_code == 200
    form_id = create_response.json()["form"]["form_id"]

    transition_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "transition_form",
            "form_id": form_id,
            "decision_key": "close",
            "actor_node_id": requester.id,
            "context": {
                "initiator_node_id": requester.id,
            },
        },
    )
    assert transition_response.status_code == 200
    transitioned = transition_response.json()["form"]
    assert transitioned["current_status"] == "ARCHIVED"
    assert transitioned["current_holder_node"] is None


def test_forms_actions_normalizes_legacy_stage_transitions_key(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspace"
    monkeypatch.setattr(FormsService, "_workspace_root", lambda self: workspace_root)
    _seed_stage_skills(
        workspace_root=workspace_root,
        type_key="legacy_transitions_form",
        skill_names=["draft-internal-message"],
    )

    database_url = f"sqlite:///{tmp_path / 'forms-legacy-transitions-normalization.db'}"
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

    upsert_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "upsert_form_type",
            "type_key": "legacy_transitions_form",
            "version": "1.0.0",
            "workflow_graph": {
                "start_stage": "DRAFT",
                "end_stage": "ARCHIVED",
                "stages": {
                    "DRAFT": {
                        "target": "{{initiator}}",
                        "required_skill": "draft-internal-message",
                        "transitions": {
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
    payload = upsert_response.json()
    assert payload["validation_errors"] == []
    draft_stage = payload["form_type"]["workflow_graph"]["stages"]["DRAFT"]
    assert draft_stage["decisions"]["close"] == "ARCHIVED"
    assert "transitions" not in draft_stage


def _seed_stage_skills(*, workspace_root: Path, type_key: str, skill_names: list[str]) -> None:
    for skill_name in skill_names:
        skill_dir = workspace_root / "forms" / type_key / "skills" / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"# {skill_name}\n\nTest fixture skill package.\n",
            encoding="utf-8",
        )


def test_forms_actions_validate_rejects_unknown_static_target_node(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspace"
    monkeypatch.setattr(FormsService, "_workspace_root", lambda self: workspace_root)
    type_key = "message_target_validation_form"
    _seed_stage_skills(
        workspace_root=workspace_root,
        type_key=type_key,
        skill_names=["draft-internal-message", "read-and-acknowledge-internal-message"],
    )

    database_url = f"sqlite:///{tmp_path / 'forms-stage-target-validate.db'}"
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

    upsert_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "upsert_form_type",
            "type_key": type_key,
            "version": "9.9.1",
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
                        "target": "Missing_Target_01",
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
    errors = upsert_response.json()["validation_errors"]
    assert any("target invalid" in str(error) for error in errors)

    activate_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "activate_form_type",
            "type_key": type_key,
            "version": "9.9.1",
        },
    )
    assert activate_response.status_code == 400
    activate_errors = activate_response.json()["detail"]["errors"]
    assert any("target invalid" in str(error) for error in activate_errors)


def test_forms_actions_activate_distributes_stage_skills_to_target_agent(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspace"
    monkeypatch.setattr(FormsService, "_workspace_root", lambda self: workspace_root)
    type_key = "message_skill_distribution_form"
    _seed_stage_skills(
        workspace_root=workspace_root,
        type_key=type_key,
        skill_names=["draft-internal-message", "read-and-acknowledge-internal-message"],
    )

    database_url = f"sqlite:///{tmp_path / 'forms-stage-skill-distribution.db'}"
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

    requester_workspace = tmp_path / "requester-workspace"
    target_workspace = tmp_path / "target-workspace"
    requester_workspace.mkdir(parents=True, exist_ok=True)
    target_workspace.mkdir(parents=True, exist_ok=True)

    repository.create_node(
        node_type=NodeType.AGENT,
        name="Requester_Distribution_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(requester_workspace.resolve()),
    )
    repository.create_node(
        node_type=NodeType.AGENT,
        name="Target_Distribution_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(target_workspace.resolve()),
    )

    target_skill_file = (
        target_workspace
        / "skills"
        / "read-and-acknowledge-internal-message"
        / "SKILL.md"
    )
    assert target_skill_file.exists() is False

    client = TestClient(app)
    upsert_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "upsert_form_type",
            "type_key": type_key,
            "version": "9.9.2",
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
                        "target": "Target_Distribution_01",
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
            "type_key": type_key,
            "version": "9.9.2",
        },
    )
    assert activate_response.status_code == 200
    assert target_skill_file.exists()


def test_forms_actions_activate_records_form_stage_assignments_and_restores_skill_sync(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace_root = tmp_path / "workspace"
    monkeypatch.setattr(FormsService, "_workspace_root", lambda self: workspace_root)
    type_key = "message_skill_assignment_restore_form"
    _seed_stage_skills(
        workspace_root=workspace_root,
        type_key=type_key,
        skill_names=["draft-internal-message", "read-and-acknowledge-internal-message"],
    )

    database_url = f"sqlite:///{tmp_path / 'forms-stage-skill-restore.db'}"
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

    target_workspace = tmp_path / "target-restore-workspace"
    target_workspace.mkdir(parents=True, exist_ok=True)
    target = repository.create_node(
        node_type=NodeType.AGENT,
        name="Target_Restore_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(target_workspace.resolve()),
    )

    client = TestClient(app)
    upsert_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "upsert_form_type",
            "type_key": type_key,
            "version": "9.9.3",
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
                        "target": "Target_Restore_01",
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
            "type_key": type_key,
            "version": "9.9.3",
        },
    )
    assert activate_response.status_code == 200

    cataloged_skill = repository.get_master_skill(name="read-and-acknowledge-internal-message")
    assert cataloged_skill is not None
    assert cataloged_skill.form_type_key == type_key

    assignments = repository.list_node_skill_assignments(
        node_id=target.id,
        assignment_source=NodeSkillAssignmentSource.FORM_STAGE,
    )
    assigned_skill_ids = {assignment.skill_id for assignment in assignments}
    assert cataloged_skill.id in assigned_skill_ids

    skills_root = target_workspace / "skills"
    synced_skill = skills_root / "read-and-acknowledge-internal-message" / "SKILL.md"
    assert synced_skill.exists()

    shutil.rmtree(skills_root)
    assert synced_skill.exists() is False

    sync_response = client.post(
        "/v1/skills/actions",
        json={
            "action": "sync_agent_skills",
            "target_node_id": target.id,
        },
    )
    assert sync_response.status_code == 200
    assert sync_response.json()["sync"]["status"] == "synced"
    assert synced_skill.exists()


def test_acknowledge_message_read_accepts_actor_node_name(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "workspace"
    monkeypatch.setattr(FormsService, "_workspace_root", lambda self: workspace_root)
    type_key = "message"
    _seed_stage_skills(
        workspace_root=workspace_root,
        type_key=type_key,
        skill_names=["draft-internal-message", "read-and-acknowledge-internal-message"],
    )

    database_url = f"sqlite:///{tmp_path / 'forms-actor-node-name.db'}"
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
    initiator_workspace = tmp_path / "initiator-workspace"
    reviewer_workspace = tmp_path / "reviewer-workspace"
    initiator_workspace.mkdir(parents=True, exist_ok=True)
    reviewer_workspace.mkdir(parents=True, exist_ok=True)
    initiator = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Macos_Supervisor",
        status=NodeStatus.ACTIVE,
        workspace_root=str(initiator_workspace.resolve()),
    )
    reviewer = repository.create_node(
        node_type=NodeType.AGENT,
        name="Director_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(reviewer_workspace.resolve()),
    )

    client = TestClient(app)
    upsert_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "upsert_form_type",
            "type_key": type_key,
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
                        "target": "Director_01",
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
            "type_key": type_key,
            "version": "1.0.0",
        },
    )
    assert activate_response.status_code == 200

    create_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "create_form",
            "type_key": type_key,
            "form_id_hint": "actor-node-name-message",
            "initial_holder_node_id": initiator.id,
            "actor_node_id": initiator.id,
        },
    )
    assert create_response.status_code == 200
    form_id = create_response.json()["form"]["form_id"]

    send_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "transition_form",
            "form_id": form_id,
            "decision_key": "send",
            "actor_node_id": initiator.id,
            "context": {
                "initiator_node_id": initiator.id,
            },
        },
    )
    assert send_response.status_code == 200
    assert send_response.json()["form"]["current_status"] == "WAITING_TO_BE_READ"
    assert send_response.json()["form"]["current_holder_node"] == reviewer.id

    acknowledge_response = client.post(
        "/v1/forms/actions",
        json={
            "action": "acknowledge_message_read",
            "form_id": form_id,
            "actor_node_name": "Director_01",
            "decision_key": "acknowledge_read",
        },
    )
    assert acknowledge_response.status_code == 200
    assert acknowledge_response.json()["form"]["current_status"] == "ARCHIVED"
    assert acknowledge_response.json()["form"]["current_holder_node"] is None

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        last_event = (
            session.query(FormTransitionEvent)
            .filter(FormTransitionEvent.form_id == form_id)
            .order_by(FormTransitionEvent.sequence.desc())
            .first()
        )
        assert last_event is not None
        assert last_event.decision_key == "acknowledge_read"
        assert last_event.actor_node_id == reviewer.id


def test_forms_workspace_sync_distributes_only_stage_target_skills(tmp_path: Path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'forms-sync-targeted.db'}"

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

    macos_workspace = tmp_path / "macos-workspace"
    hr_workspace = tmp_path / "hr-workspace"
    ops_workspace = tmp_path / "ops-workspace"
    for workspace in (macos_workspace, hr_workspace, ops_workspace):
        workspace.mkdir(parents=True, exist_ok=True)

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
    repository.create_node(
        node_type=NodeType.AGENT,
        name="Ops_Head_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(ops_workspace.resolve()),
    )

    forms_root = tmp_path / "workspace-forms"
    form_type_dir = forms_root / "targeted_form"
    (form_type_dir / "skills" / "draft-only").mkdir(parents=True, exist_ok=True)
    (form_type_dir / "skills" / "hr-only").mkdir(parents=True, exist_ok=True)
    (form_type_dir / "skills" / "any-agent").mkdir(parents=True, exist_ok=True)
    (form_type_dir / "skills" / "draft-only" / "SKILL.md").write_text(
        "---\nname: draft-only\ndescription: Draft stage skill.\n---\n\n# skill\n",
        encoding="utf-8",
    )
    (form_type_dir / "skills" / "hr-only" / "SKILL.md").write_text(
        "---\nname: hr-only\ndescription: HR stage skill.\n---\n\n# skill\n",
        encoding="utf-8",
    )
    (form_type_dir / "skills" / "any-agent" / "SKILL.md").write_text(
        "---\nname: any-agent\ndescription: Any-agent stage skill.\n---\n\n# skill\n",
        encoding="utf-8",
    )
    (form_type_dir / "workflow.json").write_text(
        json.dumps(
            {
                "form_type": "targeted_form",
                "version": "1.0.0",
                "description": "Targeted distribution workflow",
                "initiator_allowlist": ["Macos_Supervisor"],
                "start_stage": "DRAFT",
                "end_stage": "ARCHIVED",
                "stages": {
                    "DRAFT": {
                        "target": "{{initiator}}",
                        "required_skill": "draft-only",
                        "decisions": {"to_hr": "HR_REVIEW"},
                    },
                    "HR_REVIEW": {
                        "target": "HR_Head_01",
                        "required_skill": "hr-only",
                        "decisions": {"to_any": "ANY_REVIEW"},
                    },
                    "ANY_REVIEW": {
                        "target": "{{any}}",
                        "required_skill": "any-agent",
                        "decisions": {"archive": "ARCHIVED"},
                    },
                    "ARCHIVED": {
                        "is_terminal": True,
                        "target": None,
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(FormsService, "_workspace_forms_root", lambda self: forms_root)
    client = TestClient(app)
    response = client.post("/v1/forms/workspace/sync", json={"activate": True, "prune_missing": False})
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["failed"] == 0

    assert (macos_workspace / "skills" / "draft-only" / "SKILL.md").exists()
    assert not (macos_workspace / "skills" / "hr-only" / "SKILL.md").exists()
    assert not (macos_workspace / "skills" / "any-agent" / "SKILL.md").exists()

    assert not (hr_workspace / "skills" / "draft-only" / "SKILL.md").exists()
    assert (hr_workspace / "skills" / "hr-only" / "SKILL.md").exists()
    assert (hr_workspace / "skills" / "any-agent" / "SKILL.md").exists()

    assert not (ops_workspace / "skills" / "draft-only" / "SKILL.md").exists()
    assert not (ops_workspace / "skills" / "hr-only" / "SKILL.md").exists()
    assert (ops_workspace / "skills" / "any-agent" / "SKILL.md").exists()


def test_forms_workspace_sync_distributed_deploy_wrapper_finds_repo_root(
    tmp_path: Path, monkeypatch
) -> None:
    database_url = f"sqlite:///{tmp_path / 'forms-sync-deploy-wrapper.db'}"

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

    macos_workspace = tmp_path / "macos-workspace"
    ops_workspace = tmp_path / "ops-workspace"
    for workspace in (macos_workspace, ops_workspace):
        workspace.mkdir(parents=True, exist_ok=True)

    repository.create_node(
        node_type=NodeType.HUMAN,
        name="Macos_Supervisor",
        status=NodeStatus.ACTIVE,
        workspace_root=str(macos_workspace.resolve()),
    )
    repository.create_node(
        node_type=NodeType.AGENT,
        name="Ops_Head_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str(ops_workspace.resolve()),
    )

    forms_root = tmp_path / "workspace-forms"
    form_type_dir = forms_root / "deploy_wrapper_form"
    draft_skill_dir = form_type_dir / "skills" / "draft-only"
    deploy_skill_dir = form_type_dir / "skills" / "deploy-new-nanobot"
    draft_skill_dir.mkdir(parents=True, exist_ok=True)
    draft_skill_dir.joinpath("SKILL.md").write_text(
        "---\nname: draft-only\ndescription: Draft stage skill.\n---\n\n# skill\n",
        encoding="utf-8",
    )
    shutil.copytree(
        ROOT / "workspace" / "forms" / "deploy_new_agent" / "skills" / "deploy-new-nanobot",
        deploy_skill_dir,
        dirs_exist_ok=True,
    )
    (form_type_dir / "workflow.json").write_text(
        json.dumps(
            {
                "form_type": "deploy_wrapper_form",
                "version": "1.0.0",
                "description": "Deploy wrapper distribution test",
                "initiator_allowlist": ["Macos_Supervisor"],
                "start_stage": "BUSINESS_CASE",
                "end_stage": "ARCHIVED",
                "stages": {
                    "BUSINESS_CASE": {
                        "target": "{{initiator}}",
                        "required_skill": "draft-only",
                        "decisions": {"submit": "AGENT_DEPLOYMENT"},
                    },
                    "AGENT_DEPLOYMENT": {
                        "target": "Ops_Head_01",
                        "required_skill": "deploy-new-nanobot",
                        "decisions": {"archive": "ARCHIVED"},
                    },
                    "ARCHIVED": {
                        "is_terminal": True,
                        "target": None,
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(FormsService, "_workspace_forms_root", lambda self: forms_root)
    client = TestClient(app)
    response = client.post("/v1/forms/workspace/sync", json={"activate": True, "prune_missing": False})
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["failed"] == 0

    for script_name in (
        "deploy_new_nanobot.sh",
        "deploy_new_nanobot_agent.sh",
        "provision_agent_workflow.sh",
    ):
        wrapper = ops_workspace / "skills" / "deploy-new-nanobot" / "scripts" / script_name
        assert wrapper.exists()
        result = subprocess.run(
            ["bash", str(wrapper), "--help"],
            capture_output=True,
            check=False,
            env={**os.environ, "OMNICLAW_REPO_ROOT": str(ROOT)},
            text=True,
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout
