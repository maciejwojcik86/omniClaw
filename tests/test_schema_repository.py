from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import inspect, text


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.db.enums import (
    FormStatus,
    FormTypeLifecycle,
    MasterSkillLifecycleStatus,
    NodeSkillAssignmentSource,
    NodeStatus,
    NodeType,
)
from omniclaw.db.models import FormLedger
from omniclaw.db.repository import KernelRepository, TransitionConflictError
from omniclaw.db.session import create_engine_from_url, create_session_factory, init_db


def test_repository_creates_nodes_and_hierarchy(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'repo.db'}"
    engine = create_engine_from_url(database_url)
    init_db(engine)

    repository = KernelRepository(create_session_factory(database_url))
    parent = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Human_01",
        status=NodeStatus.ACTIVE,
    )
    child = repository.create_node(
        node_type=NodeType.AGENT,
        name="Agent_01",
        status=NodeStatus.PROBATION,
        linux_uid=12001,
        autonomy_level=1,
    )

    link = repository.link_manager(parent_node_id=parent.id, child_node_id=child.id)
    children = repository.list_children(parent_node_id=parent.id)

    assert link.parent_node_id == parent.id
    assert link.child_node_id == child.id
    assert len(children) == 1
    assert children[0].child_node_id == child.id


def test_alembic_upgrade_creates_canonical_tables(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    engine = create_engine_from_url(database_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    assert {
        "nodes",
        "hierarchy",
        "budgets",
        "budget_allocations",
        "budget_cycles",
        "forms_ledger",
        "form_types",
        "form_transition_events",
        "master_skills",
        "node_skill_assignments",
        "agent_llm_calls",
        "agent_session_exports",
    }.issubset(tables)

    node_columns = {column["name"] for column in inspector.get_columns("nodes")}
    assert {
        "role_name",
        "linux_username",
        "linux_password",
        "workspace_root",
        "runtime_config_path",
        "instruction_template_root",
        "primary_model",
        "gateway_running",
        "gateway_pid",
        "gateway_host",
        "gateway_port",
        "gateway_started_at",
        "gateway_stopped_at",
    }.issubset(node_columns)

    form_columns = {column["name"] for column in inspector.get_columns("forms_ledger")}
    assert {
        "form_type_key",
        "form_type_version",
        "version",
        "message_name",
        "sender_node_id",
        "target_node_id",
        "subject",
        "source_path",
        "delivery_path",
        "archive_path",
        "dead_letter_path",
        "queued_at",
        "routed_at",
        "archived_at",
        "dead_lettered_at",
        "failure_reason",
    }.issubset(form_columns)

    master_skill_columns = {column["name"] for column in inspector.get_columns("master_skills")}
    assert {
        "name",
        "form_type_key",
        "master_path",
        "description",
        "version",
        "validation_status",
        "lifecycle_status",
        "updated_at",
    }.issubset(master_skill_columns)

    assignment_columns = {column["name"] for column in inspector.get_columns("node_skill_assignments")}
    assert {
        "node_id",
        "skill_id",
        "assignment_source",
        "assigned_by_node_id",
        "updated_at",
    }.issubset(assignment_columns)

    budget_columns = {column["name"] for column in inspector.get_columns("budgets")}
    assert {
        "budget_mode",
        "rollover_reserve_usd",
        "review_required_at",
    }.issubset(budget_columns)


def test_alembic_renames_runtime_config_column_without_data_loss(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime-config-rename.db'}"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "20260305_0009")

    engine = create_engine_from_url(database_url)
    with engine.begin() as connection:
        pre_columns = {column["name"] for column in inspect(connection).get_columns("nodes")}
        assert "nullclaw_config_path" in pre_columns
        assert "runtime_config_path" not in pre_columns

        connection.execute(
            text(
                """
                INSERT INTO nodes (
                    id,
                    type,
                    name,
                    autonomy_level,
                    status,
                    nullclaw_config_path
                )
                VALUES (
                    :id,
                    :type,
                    :name,
                    :autonomy_level,
                    :status,
                    :nullclaw_config_path
                )
                """
            ),
            {
                "id": "runtime-rename-node",
                "type": NodeType.AGENT.value,
                "name": "Director_01",
                "autonomy_level": 2,
                "status": NodeStatus.ACTIVE.value,
                "nullclaw_config_path": "/tmp/director/config.json",
            },
        )

    command.upgrade(config, "head")

    upgraded_engine = create_engine_from_url(database_url)
    upgraded_columns = {column["name"] for column in inspect(upgraded_engine).get_columns("nodes")}
    assert "runtime_config_path" in upgraded_columns
    assert "nullclaw_config_path" not in upgraded_columns

    with upgraded_engine.connect() as connection:
        stored_path = connection.execute(
            text("SELECT runtime_config_path FROM nodes WHERE id = :id"),
            {"id": "runtime-rename-node"},
        ).scalar_one()

    assert stored_path == "/tmp/director/config.json"


def test_repository_enforces_single_line_manager(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'line-manager.db'}"
    engine = create_engine_from_url(database_url)
    init_db(engine)
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
    worker = repository.create_node(
        node_type=NodeType.AGENT,
        name="Worker_01",
        status=NodeStatus.ACTIVE,
    )

    repository.link_manager(parent_node_id=manager_one.id, child_node_id=worker.id)
    with pytest.raises(ValueError, match="already has manager"):
        repository.link_manager(parent_node_id=manager_two.id, child_node_id=worker.id)


def test_repository_persists_node_instruction_metadata(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'instruction-metadata.db'}"
    engine = create_engine_from_url(database_url)
    init_db(engine)
    repository = KernelRepository(create_session_factory(database_url))

    manager = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Manager_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str((tmp_path / "workspace" / "manager").resolve()),
    )
    worker = repository.create_node(
        node_type=NodeType.AGENT,
        name="Worker_01",
        status=NodeStatus.ACTIVE,
        role_name="Worker",
        workspace_root=str((tmp_path / "workspace" / "agents" / "Worker_01" / "workspace").resolve()),
        instruction_template_root=str((tmp_path / "workspace" / "nanobots_instructions" / "Worker_01").resolve()),
    )

    repository.link_manager(parent_node_id=manager.id, child_node_id=worker.id)
    refreshed = repository.update_node_instruction_fields(
        node_id=worker.id,
        role_name="Senior Worker",
        instruction_template_root=str(
            (tmp_path / "workspace" / "nanobots_instructions" / "Worker_01_v2").resolve()
        ),
    )

    assert refreshed.role_name == "Senior Worker"
    assert refreshed.instruction_template_root == str(
        (tmp_path / "workspace" / "nanobots_instructions" / "Worker_01_v2").resolve()
    )

    children = repository.list_child_nodes(parent_node_id=manager.id)
    manager_node = repository.get_manager_node(child_node_id=worker.id)
    assert len(children) == 1
    assert children[0].name == "Worker_01"
    assert manager_node is not None
    assert manager_node.name == "Manager_01"


def test_repository_creates_message_ledger_entries(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'message-ledger.db'}"
    engine = create_engine_from_url(database_url)
    init_db(engine)
    repository = KernelRepository(create_session_factory(database_url))

    sender = repository.create_node(
        node_type=NodeType.AGENT,
        name="Sender_01",
        status=NodeStatus.ACTIVE,
        workspace_root="/tmp/sender",
    )
    target = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Manager_01",
        status=NodeStatus.ACTIVE,
        workspace_root="/tmp/manager",
    )

    created = repository.create_message_ledger_entry(
        form_id="hello-world",
        current_status=FormStatus.ARCHIVED.value,
        current_holder_node=target.id,
        message_name="hello-world.md",
        sender_node_id=sender.id,
        target_node_id=target.id,
        subject="Hello",
        source_path="/tmp/sender/outbox/send/hello-world.md",
        delivery_path="/tmp/manager/inbox/new/hello-world.md",
        archive_path="/tmp/sender/outbox/archive/hello-world.md",
        dead_letter_path=None,
        queued_at=None,
        routed_at=None,
        archived_at=None,
        dead_lettered_at=None,
        failure_reason=None,
        history_log='[{"status":"QUEUED"},{"status":"ARCHIVED"}]',
    )

    assert created.form_id.startswith("hello-world")
    assert created.type == "message"
    assert created.form_type_key == "message"
    assert created.current_status == FormStatus.ARCHIVED.value
    assert created.sender_node_id == sender.id
    assert created.target_node_id == target.id

    session_factory = create_session_factory(database_url)
    with session_factory() as session:
        stored = (
            session.query(FormLedger)
            .filter(FormLedger.form_id == created.form_id)
            .order_by(FormLedger.created_at.asc())
            .first()
        )
        assert stored is not None
        assert stored.subject == "Hello"


def test_repository_upserts_form_type_and_transitions_form(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'form-state.db'}"
    engine = create_engine_from_url(database_url)
    init_db(engine)
    repository = KernelRepository(create_session_factory(database_url))

    owner = repository.create_node(
        node_type=NodeType.HUMAN,
        name="Owner_01",
        status=NodeStatus.ACTIVE,
    )
    reviewer = repository.create_node(
        node_type=NodeType.AGENT,
        name="Reviewer_01",
        status=NodeStatus.ACTIVE,
    )

    definition = repository.upsert_form_type_definition(
        type_key="feature_pipeline_form",
        version="1.0.0",
        lifecycle_state=FormTypeLifecycle.DRAFT,
        workflow_graph={
            "initial_status": "DRAFT",
            "edges": [
                {
                    "from": "DRAFT",
                    "to": "PLANNED",
                    "decision": "submit",
                    "next_holder": {"strategy": "field_ref", "value": "implementer_node_id"},
                }
            ],
        },
        stage_metadata={
            "DRAFT": {
                "stage_skill_ref": ".codex/skills/form-type-authoring/SKILL.md",
                "stage_template_ref": "templates/forms/feature_pipeline_form/draft.md",
            },
            "PLANNED": {
                "stage_skill_ref": ".codex/skills/form-stage-execution/SKILL.md",
                "stage_template_ref": "templates/forms/feature_pipeline_form/planned.md",
            },
        },
        description="Feature pipeline form",
        validation_errors=None,
    )
    assert definition.type_key == "feature_pipeline_form"

    created = repository.create_form_instance(
        form_id_hint="feature-pipeline-001",
        form_type_key="feature_pipeline_form",
        form_type_version="1.0.0",
        current_status="DRAFT",
        current_holder_node=owner.id,
        actor_node_id=owner.id,
        decision_key="create",
        event_payload={"hello": "world"},
        message_name=None,
        sender_node_id=owner.id,
        target_node_id=reviewer.id,
        subject=None,
        source_path=None,
        delivery_path=None,
        archive_path=None,
        dead_letter_path=None,
        queued_at=None,
        routed_at=None,
        archived_at=None,
        dead_lettered_at=None,
        failure_reason=None,
    )
    assert created.current_status == "DRAFT"
    assert created.current_holder_node == owner.id

    transitioned = repository.transition_form_instance(
        form_id=created.form_id,
        expected_from_status="DRAFT",
        to_status="PLANNED",
        new_holder_node_id=reviewer.id,
        actor_node_id=owner.id,
        decision_key="submit",
        event_payload={"ready": True},
    )
    assert transitioned.current_status == "PLANNED"
    assert transitioned.current_holder_node == reviewer.id

    events = repository.list_form_transition_events(form_id=created.form_id)
    assert len(events) == 2
    assert events[0].to_status == "DRAFT"
    assert events[1].to_status == "PLANNED"


def test_repository_rejects_stale_transition_state(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'form-transition-conflict.db'}"
    engine = create_engine_from_url(database_url)
    init_db(engine)
    repository = KernelRepository(create_session_factory(database_url))

    owner = repository.create_node(
        node_type=NodeType.AGENT,
        name="Conflict_Owner",
        status=NodeStatus.ACTIVE,
    )

    created = repository.create_form_instance(
        form_id_hint="stale-state",
        form_type_key="message",
        form_type_version="1.0.0",
        current_status="DRAFT",
        current_holder_node=owner.id,
        actor_node_id=owner.id,
        decision_key="create",
        event_payload=None,
        message_name=None,
        sender_node_id=owner.id,
        target_node_id=owner.id,
        subject=None,
        source_path=None,
        delivery_path=None,
        archive_path=None,
        dead_letter_path=None,
        queued_at=None,
        routed_at=None,
        archived_at=None,
        dead_lettered_at=None,
        failure_reason=None,
    )
    repository.transition_form_instance(
        form_id=created.form_id,
        expected_from_status="DRAFT",
        to_status="WAITING_TO_BE_READ",
        new_holder_node_id=owner.id,
        actor_node_id=owner.id,
        decision_key="send",
        event_payload=None,
    )

    with pytest.raises(TransitionConflictError, match="concurrent transition conflict"):
        repository.transition_form_instance(
            form_id=created.form_id,
            expected_from_status="DRAFT",
            to_status="ARCHIVED",
            new_holder_node_id=None,
            actor_node_id=owner.id,
            decision_key="close",
            event_payload=None,
        )


def test_repository_resolves_unique_node_reference(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'resolve-node-reference.db'}"
    engine = create_engine_from_url(database_url)
    init_db(engine)
    repository = KernelRepository(create_session_factory(database_url))

    node = repository.create_node(
        node_type=NodeType.AGENT,
        name="Resolver_Node",
        status=NodeStatus.ACTIVE,
    )

    by_name, error_by_name = repository.resolve_unique_node_reference("Resolver_Node")
    assert error_by_name is None
    assert by_name is not None
    assert by_name.id == node.id

    by_id, error_by_id = repository.resolve_unique_node_reference(node.id)
    assert error_by_id is None
    assert by_id is not None
    assert by_id.id == node.id

    missing, missing_error = repository.resolve_unique_node_reference("missing-node")
    assert missing is None
    assert missing_error == "node name 'missing-node' not found"


def test_repository_persists_master_skill_lifecycle_and_assignments(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'skill-repository.db'}"
    engine = create_engine_from_url(database_url)
    init_db(engine)
    repository = KernelRepository(create_session_factory(database_url))

    agent = repository.create_node(
        node_type=NodeType.AGENT,
        name="Skill_Node_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str((tmp_path / "workspace" / "agents" / "Skill_Node_01" / "workspace").resolve()),
    )

    loose_skill = repository.upsert_master_skill(
        name="skill-alpha",
        form_type_key=None,
        master_path=str((tmp_path / "workspace" / "master_skills" / "skill-alpha").resolve()),
        description="Alpha skill",
        version="1.0.0",
        lifecycle_status=MasterSkillLifecycleStatus.ACTIVE,
    )
    form_skill = repository.upsert_master_skill(
        name="stage-skill-beta",
        form_type_key="deploy_new_agent",
        master_path=str((tmp_path / "workspace" / "forms" / "deploy_new_agent" / "skills" / "stage-skill-beta").resolve()),
        description="Stage skill",
        version="1.0.0",
        lifecycle_status=MasterSkillLifecycleStatus.ACTIVE,
    )

    repository.upsert_node_skill_assignment(
        node_id=agent.id,
        skill_id=loose_skill.id,
        assignment_source=NodeSkillAssignmentSource.MANUAL,
    )
    repository.upsert_node_skill_assignment(
        node_id=agent.id,
        skill_id=form_skill.id,
        assignment_source=NodeSkillAssignmentSource.FORM_STAGE,
    )

    details = repository.list_node_skill_assignment_details(node_id=agent.id)
    assert len(details) == 2
    assert {skill.name for _, skill in details} == {"skill-alpha", "stage-skill-beta"}

    updated_skill = repository.set_master_skill_lifecycle_status(
        name="skill-alpha",
        lifecycle_status=MasterSkillLifecycleStatus.DEACTIVATED,
    )
    assert updated_skill.lifecycle_status == MasterSkillLifecycleStatus.DEACTIVATED

    repository.delete_node_skill_assignments(
        node_id=agent.id,
        skill_ids=[loose_skill.id],
        assignment_source=NodeSkillAssignmentSource.MANUAL,
    )
    remaining = repository.list_node_skill_assignment_details(node_id=agent.id)
    assert len(remaining) == 1
    assert remaining[0][1].name == "stage-skill-beta"
