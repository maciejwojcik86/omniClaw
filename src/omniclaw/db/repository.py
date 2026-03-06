from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from omniclaw.db.enums import (
    FormStatus,
    FormTypeLifecycle,
    NodeStatus,
    NodeType,
    RelationshipType,
    SkillValidationStatus,
)
from omniclaw.db.models import FormLedger, FormTransitionEvent, FormTypeDefinition, Hierarchy, MasterSkill, Node


class TransitionConflictError(RuntimeError):
    pass


class KernelRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def create_node(
        self,
        *,
        node_type: NodeType,
        name: str,
        status: NodeStatus,
        linux_uid: int | None = None,
        linux_username: str | None = None,
        linux_password: str | None = None,
        workspace_root: str | None = None,
        runtime_config_path: str | None = None,
        primary_model: str | None = None,
        autonomy_level: int = 0,
    ) -> Node:
        with self._session_factory() as session:
            node = Node(
                type=node_type,
                name=name,
                status=status,
                linux_uid=linux_uid,
                linux_username=linux_username,
                linux_password=linux_password,
                workspace_root=workspace_root,
                runtime_config_path=runtime_config_path,
                primary_model=primary_model,
                autonomy_level=autonomy_level,
            )
            session.add(node)
            session.commit()
            session.refresh(node)
            return node

    def upsert_node_by_name(
        self,
        *,
        node_type: NodeType,
        name: str,
        status: NodeStatus,
        linux_uid: int | None = None,
        linux_username: str | None = None,
        linux_password: str | None = None,
        workspace_root: str | None = None,
        runtime_config_path: str | None = None,
        primary_model: str | None = None,
        autonomy_level: int = 0,
    ) -> tuple[Node, bool]:
        with self._session_factory() as session:
            existing = (
                session.query(Node)
                .filter(Node.type == node_type, Node.name == name)
                .order_by(Node.created_at.asc())
                .first()
            )
            if existing is not None:
                existing.status = status
                existing.linux_uid = linux_uid
                existing.linux_username = linux_username
                if linux_password is not None:
                    existing.linux_password = linux_password
                existing.workspace_root = workspace_root
                existing.runtime_config_path = runtime_config_path
                existing.primary_model = primary_model
                existing.autonomy_level = autonomy_level
                session.commit()
                session.refresh(existing)
                return existing, False

            created = Node(
                type=node_type,
                name=name,
                status=status,
                linux_uid=linux_uid,
                linux_username=linux_username,
                linux_password=linux_password,
                workspace_root=workspace_root,
                runtime_config_path=runtime_config_path,
                primary_model=primary_model,
                autonomy_level=autonomy_level,
            )
            session.add(created)
            session.commit()
            session.refresh(created)
            return created, True

    def link_manager(
        self,
        *,
        parent_node_id: str,
        child_node_id: str,
        relationship_type: RelationshipType = RelationshipType.MANAGES,
    ) -> Hierarchy:
        with self._session_factory() as session:
            return self._link_manager_internal(
                session=session,
                parent_node_id=parent_node_id,
                child_node_id=child_node_id,
                relationship_type=relationship_type,
            )

    def link_manager_if_missing(
        self,
        *,
        parent_node_id: str,
        child_node_id: str,
        relationship_type: RelationshipType = RelationshipType.MANAGES,
    ) -> Hierarchy:
        with self._session_factory() as session:
            return self._link_manager_internal(
                session=session,
                parent_node_id=parent_node_id,
                child_node_id=child_node_id,
                relationship_type=relationship_type,
            )

    def resolve_unique_node_reference(self, value: str) -> tuple[Node | None, str | None]:
        raw = value.strip()
        if not raw:
            return None, "node reference is empty"

        if self._looks_like_uuid(raw):
            node = self.get_node(node_id=raw)
            if node is None:
                return None, f"node id '{raw}' not found"
            return node, None

        matches = self.list_nodes_by_name(node_name=raw)
        if not matches:
            return None, f"node name '{raw}' not found"
        if len(matches) > 1:
            return None, f"node name '{raw}' is not unique ({len(matches)} matches)"
        return matches[0], None

    def list_children(self, *, parent_node_id: str) -> list[Hierarchy]:
        with self._session_factory() as session:
            return (
                session.query(Hierarchy)
                .filter(Hierarchy.parent_node_id == parent_node_id)
                .order_by(Hierarchy.created_at.asc())
                .all()
            )

    def get_node(
        self,
        *,
        node_id: str | None = None,
        node_name: str | None = None,
        node_type: NodeType | None = None,
    ) -> Node | None:
        if not node_id and not node_name:
            raise ValueError("node_id or node_name is required")

        with self._session_factory() as session:
            query = session.query(Node)
            if node_type is not None:
                query = query.filter(Node.type == node_type)
            if node_id:
                query = query.filter(Node.id == node_id)
            else:
                query = query.filter(Node.name == node_name)
            return query.order_by(Node.created_at.asc()).first()

    def get_agent_node(self, *, node_id: str | None = None, node_name: str | None = None) -> Node | None:
        if not node_id and not node_name:
            raise ValueError("node_id or node_name is required")

        with self._session_factory() as session:
            query = session.query(Node).filter(Node.type == NodeType.AGENT)
            if node_id:
                query = query.filter(Node.id == node_id)
            else:
                query = query.filter(Node.name == node_name)
            return query.order_by(Node.created_at.asc()).first()

    def list_agent_nodes(self) -> list[Node]:
        with self._session_factory() as session:
            return (
                session.query(Node)
                .filter(Node.type == NodeType.AGENT)
                .order_by(Node.created_at.asc())
                .all()
            )

    def list_nodes_with_workspaces(self) -> list[Node]:
        with self._session_factory() as session:
            return (
                session.query(Node)
                .filter(Node.workspace_root.is_not(None))
                .order_by(Node.created_at.asc())
                .all()
            )

    def list_active_agent_nodes_with_workspaces(self) -> list[Node]:
        with self._session_factory() as session:
            return (
                session.query(Node)
                .filter(
                    Node.type == NodeType.AGENT,
                    Node.status == NodeStatus.ACTIVE,
                    Node.workspace_root.is_not(None),
                )
                .order_by(Node.created_at.asc())
                .all()
            )

    def list_nodes_by_name(self, *, node_name: str) -> list[Node]:
        with self._session_factory() as session:
            return (
                session.query(Node)
                .filter(Node.name == node_name)
                .order_by(Node.created_at.asc())
                .all()
            )

    def has_direct_management_link(self, *, sender_node_id: str, target_node_id: str) -> bool:
        with self._session_factory() as session:
            link = (
                session.query(Hierarchy)
                .filter(
                    ((Hierarchy.parent_node_id == sender_node_id) & (Hierarchy.child_node_id == target_node_id))
                    | ((Hierarchy.parent_node_id == target_node_id) & (Hierarchy.child_node_id == sender_node_id))
                )
                .order_by(Hierarchy.created_at.asc())
                .first()
            )
            return link is not None

    # ---------------------------------------------------------------------
    # Form type registry operations
    # ---------------------------------------------------------------------

    def upsert_form_type_definition(
        self,
        *,
        type_key: str,
        version: str,
        lifecycle_state: FormTypeLifecycle,
        workflow_graph: dict[str, Any],
        stage_metadata: dict[str, Any],
        description: str | None = None,
        validation_errors: list[str] | None = None,
    ) -> FormTypeDefinition:
        with self._session_factory() as session:
            existing = (
                session.query(FormTypeDefinition)
                .filter(FormTypeDefinition.type_key == type_key, FormTypeDefinition.version == version)
                .order_by(FormTypeDefinition.created_at.asc())
                .first()
            )
            encoded_errors = json.dumps(validation_errors) if validation_errors is not None else None
            if existing is None:
                existing = FormTypeDefinition(
                    type_key=type_key,
                    version=version,
                    lifecycle_state=lifecycle_state,
                    description=description,
                    workflow_graph=json.dumps(workflow_graph),
                    stage_metadata=json.dumps(stage_metadata),
                    validation_errors=encoded_errors,
                )
                session.add(existing)
            else:
                existing.lifecycle_state = lifecycle_state
                existing.description = description
                existing.workflow_graph = json.dumps(workflow_graph)
                existing.stage_metadata = json.dumps(stage_metadata)
                existing.validation_errors = encoded_errors
            session.commit()
            session.refresh(existing)
            return existing

    def get_form_type_definition(
        self,
        *,
        type_key: str,
        version: str | None = None,
        active_only: bool = False,
    ) -> FormTypeDefinition | None:
        with self._session_factory() as session:
            query = session.query(FormTypeDefinition).filter(FormTypeDefinition.type_key == type_key)
            if version is not None:
                query = query.filter(FormTypeDefinition.version == version)
            if active_only:
                query = query.filter(FormTypeDefinition.lifecycle_state == FormTypeLifecycle.ACTIVE)
            return query.order_by(FormTypeDefinition.created_at.asc()).first()

    def list_form_type_definitions(self, *, type_key: str | None = None) -> list[FormTypeDefinition]:
        with self._session_factory() as session:
            query = session.query(FormTypeDefinition)
            if type_key is not None:
                query = query.filter(FormTypeDefinition.type_key == type_key)
            return (
                query.order_by(
                    FormTypeDefinition.type_key.asc(),
                    FormTypeDefinition.created_at.asc(),
                ).all()
            )

    def set_form_type_lifecycle(
        self,
        *,
        type_key: str,
        version: str,
        lifecycle_state: FormTypeLifecycle,
        validation_errors: list[str] | None = None,
        deactivate_others: bool = False,
    ) -> FormTypeDefinition:
        with self._session_factory() as session:
            definition = (
                session.query(FormTypeDefinition)
                .filter(FormTypeDefinition.type_key == type_key, FormTypeDefinition.version == version)
                .order_by(FormTypeDefinition.created_at.asc())
                .first()
            )
            if definition is None:
                raise ValueError(f"form type '{type_key}' version '{version}' not found")

            if deactivate_others and lifecycle_state == FormTypeLifecycle.ACTIVE:
                (
                    session.query(FormTypeDefinition)
                    .filter(
                        FormTypeDefinition.type_key == type_key,
                        FormTypeDefinition.version != version,
                        FormTypeDefinition.lifecycle_state == FormTypeLifecycle.ACTIVE,
                    )
                    .update({"lifecycle_state": FormTypeLifecycle.VALIDATED}, synchronize_session=False)
                )

            definition.lifecycle_state = lifecycle_state
            definition.validation_errors = json.dumps(validation_errors) if validation_errors is not None else None
            session.commit()
            session.refresh(definition)
            return definition

    def delete_form_type_definition(self, *, type_key: str, version: str) -> bool:
        with self._session_factory() as session:
            definition = (
                session.query(FormTypeDefinition)
                .filter(FormTypeDefinition.type_key == type_key, FormTypeDefinition.version == version)
                .order_by(FormTypeDefinition.created_at.asc())
                .first()
            )
            if definition is None:
                return False
            session.delete(definition)
            session.commit()
            return True

    def count_form_instances_for_type_version(self, *, type_key: str, version: str) -> int:
        with self._session_factory() as session:
            return (
                session.query(FormLedger)
                .filter(
                    FormLedger.form_type_key == type_key,
                    FormLedger.form_type_version == version,
                )
                .count()
            )

    def ensure_builtin_message_form_type(self) -> FormTypeDefinition:
        active = self.get_form_type_definition(type_key="message", active_only=True)
        if active is not None:
            return active

        existing = self.get_form_type_definition(type_key="message")
        if existing is not None:
            raise ValueError(
                "message form type exists but has no ACTIVE version; "
                "activate one via /v1/forms/actions"
            )

        workflow_package = self._load_workspace_form_package(type_key="message")
        if workflow_package is None:
            raise ValueError(
                "message form type is missing and no workspace workflow exists at "
                "'workspace/forms/message/workflow.json'; publish and activate a message workflow"
            )

        workflow_graph: dict[str, Any]
        raw_graph = workflow_package.get("workflow_graph")
        if isinstance(raw_graph, dict):
            workflow_graph = raw_graph
        else:
            workflow_graph = workflow_package

        raw_description = workflow_package.get("description")
        description = raw_description if isinstance(raw_description, str) and raw_description.strip() else None
        raw_version = workflow_package.get("version")
        version = str(raw_version).strip() if raw_version is not None and str(raw_version).strip() else "1.0.0"
        raw_stage_metadata = workflow_package.get("stage_metadata")
        stage_metadata = raw_stage_metadata if isinstance(raw_stage_metadata, dict) else {}

        return self.upsert_form_type_definition(
            type_key="message",
            version=version,
            lifecycle_state=FormTypeLifecycle.ACTIVE,
            description=description,
            workflow_graph=workflow_graph,
            stage_metadata=stage_metadata,
        )

    # ---------------------------------------------------------------------
    # Master skill catalog operations
    # ---------------------------------------------------------------------

    def upsert_master_skill(
        self,
        *,
        name: str,
        form_type_key: str | None,
        master_path: str,
        description: str | None,
        version: str,
        validation_status: SkillValidationStatus = SkillValidationStatus.VALIDATED,
    ) -> MasterSkill:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("master skill name is required")

        normalized_path = master_path.strip()
        if not normalized_path:
            raise ValueError(f"master skill '{normalized_name}' path is required")

        normalized_form_type_key = form_type_key.strip() if isinstance(form_type_key, str) else None
        if normalized_form_type_key == "":
            normalized_form_type_key = None
        normalized_description = description.strip() if isinstance(description, str) and description.strip() else None
        normalized_version = version.strip() if isinstance(version, str) and version.strip() else "1.0.0"

        with self._session_factory() as session:
            existing = (
                session.query(MasterSkill)
                .filter(MasterSkill.name == normalized_name)
                .order_by(MasterSkill.created_at.asc())
                .first()
            )
            if existing is None:
                existing = MasterSkill(
                    name=normalized_name,
                    form_type_key=normalized_form_type_key,
                    master_path=normalized_path,
                    description=normalized_description,
                    version=normalized_version,
                    validation_status=validation_status,
                )
                session.add(existing)
            else:
                existing.form_type_key = normalized_form_type_key
                existing.master_path = normalized_path
                existing.description = normalized_description
                existing.version = normalized_version
                existing.validation_status = validation_status
            session.commit()
            session.refresh(existing)
            return existing

    def list_master_skills(self, *, form_type_key: str | None = None) -> list[MasterSkill]:
        with self._session_factory() as session:
            query = session.query(MasterSkill)
            if form_type_key is not None:
                query = query.filter(MasterSkill.form_type_key == form_type_key)
            return query.order_by(MasterSkill.name.asc(), MasterSkill.created_at.asc()).all()

    # ---------------------------------------------------------------------
    # Form ledger and transition events
    # ---------------------------------------------------------------------

    def get_form_ledger(self, *, form_id: str) -> FormLedger | None:
        with self._session_factory() as session:
            return (
                session.query(FormLedger)
                .filter(FormLedger.form_id == form_id)
                .order_by(FormLedger.created_at.asc())
                .first()
            )

    def list_form_transition_events(self, *, form_id: str) -> list[FormTransitionEvent]:
        with self._session_factory() as session:
            return (
                session.query(FormTransitionEvent)
                .filter(FormTransitionEvent.form_id == form_id)
                .order_by(FormTransitionEvent.sequence.asc(), FormTransitionEvent.created_at.asc())
                .all()
            )

    def create_form_instance(
        self,
        *,
        form_id_hint: str,
        form_type_key: str,
        form_type_version: str,
        current_status: str,
        current_holder_node: str | None,
        actor_node_id: str | None,
        decision_key: str | None,
        event_payload: dict[str, Any] | None,
        message_name: str | None,
        sender_node_id: str | None,
        target_node_id: str | None,
        subject: str | None,
        source_path: str | None,
        delivery_path: str | None,
        archive_path: str | None,
        dead_letter_path: str | None,
        queued_at: datetime | None,
        routed_at: datetime | None,
        archived_at: datetime | None,
        dead_lettered_at: datetime | None,
        failure_reason: str | None,
        event_time: datetime | None = None,
    ) -> FormLedger:
        created_at = event_time or datetime.now(timezone.utc)
        with self._session_factory() as session:
            candidate_form_id = self._next_available_form_id(session, form_id_hint)
            entry = FormLedger(
                form_id=candidate_form_id,
                type=form_type_key,
                form_type_key=form_type_key,
                form_type_version=form_type_version,
                current_status=current_status,
                current_holder_node=current_holder_node,
                message_name=message_name,
                sender_node_id=sender_node_id,
                target_node_id=target_node_id,
                subject=subject,
                source_path=source_path,
                delivery_path=delivery_path,
                archive_path=archive_path,
                dead_letter_path=dead_letter_path,
                queued_at=queued_at,
                routed_at=routed_at,
                archived_at=archived_at,
                dead_lettered_at=dead_lettered_at,
                failure_reason=failure_reason,
                history_log=json.dumps([{"status": current_status, "at": created_at.isoformat()}]),
            )
            session.add(entry)

            event = FormTransitionEvent(
                form_id=candidate_form_id,
                sequence=1,
                from_status=None,
                to_status=current_status,
                decision_key=decision_key,
                actor_node_id=actor_node_id,
                previous_holder_node_id=None,
                new_holder_node_id=current_holder_node,
                payload_json=json.dumps(event_payload) if event_payload is not None else None,
                created_at=created_at,
            )
            session.add(event)
            session.commit()
            session.refresh(entry)
            return entry

    def transition_form_instance(
        self,
        *,
        form_id: str,
        expected_from_status: str,
        to_status: str,
        new_holder_node_id: str | None,
        actor_node_id: str | None,
        decision_key: str | None,
        event_payload: dict[str, Any] | None,
        set_fields: dict[str, Any] | None = None,
        event_time: datetime | None = None,
    ) -> FormLedger:
        transitioned_at = event_time or datetime.now(timezone.utc)
        with self._session_factory() as session:
            try:
                entry = (
                    session.query(FormLedger)
                    .filter(FormLedger.form_id == form_id)
                    .order_by(FormLedger.created_at.asc())
                    .first()
                )
                if entry is None:
                    raise ValueError(f"form '{form_id}' not found")
                if entry.current_status != expected_from_status:
                    raise TransitionConflictError(
                        "concurrent transition conflict: "
                        f"expected status '{expected_from_status}', got '{entry.current_status}'"
                    )

                previous_holder = entry.current_holder_node
                previous_status = entry.current_status
                entry.current_status = to_status
                entry.current_holder_node = new_holder_node_id

                if set_fields:
                    for key, value in set_fields.items():
                        if not hasattr(entry, key):
                            raise ValueError(f"unknown forms_ledger field '{key}'")
                        setattr(entry, key, value)

                history = self._safe_history_log(entry.history_log)
                history.append({"status": to_status, "at": transitioned_at.isoformat()})
                entry.history_log = json.dumps(history)

                max_sequence = (
                    session.query(func.max(FormTransitionEvent.sequence))
                    .filter(FormTransitionEvent.form_id == form_id)
                    .scalar()
                )
                sequence = int(max_sequence or 0) + 1
                event = FormTransitionEvent(
                    form_id=form_id,
                    sequence=sequence,
                    from_status=previous_status,
                    to_status=to_status,
                    decision_key=decision_key,
                    actor_node_id=actor_node_id,
                    previous_holder_node_id=previous_holder,
                    new_holder_node_id=new_holder_node_id,
                    payload_json=json.dumps(event_payload) if event_payload is not None else None,
                    created_at=transitioned_at,
                )
                session.add(event)
                session.commit()
                session.refresh(entry)
                return entry
            except (StaleDataError, IntegrityError) as exc:
                session.rollback()
                raise TransitionConflictError(
                    f"concurrent transition conflict for form '{form_id}'"
                ) from exc

    def create_message_ledger_entry(
        self,
        *,
        form_id: str,
        current_status: FormStatus | str,
        current_holder_node: str | None,
        message_name: str | None,
        sender_node_id: str | None,
        target_node_id: str | None,
        subject: str | None,
        source_path: str | None,
        delivery_path: str | None,
        archive_path: str | None,
        dead_letter_path: str | None,
        queued_at: datetime | None,
        routed_at: datetime | None,
        archived_at: datetime | None,
        dead_lettered_at: datetime | None,
        failure_reason: str | None,
        history_log: str,
    ) -> FormLedger:
        status_value = current_status.value if isinstance(current_status, FormStatus) else str(current_status)
        message_definition = self.ensure_builtin_message_form_type()
        created = self.create_form_instance(
            form_id_hint=form_id,
            form_type_key="message",
            form_type_version=message_definition.version,
            current_status=status_value,
            current_holder_node=current_holder_node,
            actor_node_id=sender_node_id,
            decision_key=None,
            event_payload=None,
            message_name=message_name,
            sender_node_id=sender_node_id,
            target_node_id=target_node_id,
            subject=subject,
            source_path=source_path,
            delivery_path=delivery_path,
            archive_path=archive_path,
            dead_letter_path=dead_letter_path,
            queued_at=queued_at,
            routed_at=routed_at,
            archived_at=archived_at,
            dead_lettered_at=dead_lettered_at,
            failure_reason=failure_reason,
            event_time=queued_at,
        )
        with self._session_factory() as session:
            entry = (
                session.query(FormLedger)
                .filter(FormLedger.form_id == created.form_id)
                .order_by(FormLedger.created_at.asc())
                .first()
            )
            if entry is None:
                raise ValueError("created form entry could not be reloaded")
            entry.history_log = history_log
            session.commit()
            session.refresh(entry)
            return entry

    # ---------------------------------------------------------------------
    # Runtime gateway state operations
    # ---------------------------------------------------------------------

    def mark_gateway_started(
        self,
        *,
        node_id: str,
        pid: int | None,
        host: str,
        port: int,
    ) -> Node:
        with self._session_factory() as session:
            node = (
                session.query(Node)
                .filter(Node.id == node_id, Node.type == NodeType.AGENT)
                .order_by(Node.created_at.asc())
                .first()
            )
            if node is None:
                raise ValueError(f"agent node '{node_id}' not found")

            node.gateway_running = True
            node.gateway_pid = pid
            node.gateway_host = host
            node.gateway_port = port
            node.gateway_started_at = datetime.now(timezone.utc)
            node.gateway_stopped_at = None
            session.commit()
            session.refresh(node)
            return node

    def mark_gateway_stopped(self, *, node_id: str) -> Node:
        with self._session_factory() as session:
            node = (
                session.query(Node)
                .filter(Node.id == node_id, Node.type == NodeType.AGENT)
                .order_by(Node.created_at.asc())
                .first()
            )
            if node is None:
                raise ValueError(f"agent node '{node_id}' not found")

            node.gateway_running = False
            node.gateway_pid = None
            node.gateway_stopped_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(node)
            return node

    def reconcile_gateway_state(
        self,
        *,
        node_id: str,
        running: bool,
        pid: int | None,
        host: str | None = None,
        port: int | None = None,
    ) -> Node:
        with self._session_factory() as session:
            node = (
                session.query(Node)
                .filter(Node.id == node_id, Node.type == NodeType.AGENT)
                .order_by(Node.created_at.asc())
                .first()
            )
            if node is None:
                raise ValueError(f"agent node '{node_id}' not found")

            node.gateway_running = running
            node.gateway_pid = pid if running else None
            if host is not None:
                node.gateway_host = host
            if port is not None:
                node.gateway_port = port
            if running:
                if node.gateway_started_at is None:
                    node.gateway_started_at = datetime.now(timezone.utc)
                node.gateway_stopped_at = None
            else:
                node.gateway_stopped_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(node)
            return node

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _next_available_form_id(self, session: Session, form_id_hint: str) -> str:
        base = self._normalize_form_id_hint(form_id_hint)
        candidate = base
        suffix = 2
        while (
            session.query(FormLedger)
            .filter(FormLedger.form_id == candidate)
            .order_by(FormLedger.created_at.asc())
            .first()
            is not None
        ):
            candidate = self._normalize_form_id_hint(f"{base}-{suffix}")
            suffix += 1
        return candidate

    def _normalize_form_id_hint(self, form_id_hint: str) -> str:
        cleaned = form_id_hint.strip().lower()
        if cleaned.endswith(".md"):
            cleaned = cleaned[: -len(".md")]
        if cleaned.endswith(".markdown"):
            cleaned = cleaned[: -len(".markdown")]
        cleaned = cleaned.replace(" ", "-")
        cleaned = re.sub(r"[^a-z0-9_-]", "", cleaned)
        cleaned = re.sub(r"-+", "-", cleaned)
        cleaned = cleaned.strip("-")
        if not cleaned:
            return "form"
        return cleaned[:64]

    def _link_manager_internal(
        self,
        *,
        session: Session,
        parent_node_id: str,
        child_node_id: str,
        relationship_type: RelationshipType,
    ) -> Hierarchy:
        existing_for_child = (
            session.query(Hierarchy)
            .filter(Hierarchy.child_node_id == child_node_id)
            .order_by(Hierarchy.created_at.asc())
            .first()
        )
        if existing_for_child is not None:
            if existing_for_child.parent_node_id == parent_node_id:
                return existing_for_child
            raise ValueError(f"child node '{child_node_id}' already has manager '{existing_for_child.parent_node_id}'")

        link = Hierarchy(
            parent_node_id=parent_node_id,
            child_node_id=child_node_id,
            relationship_type=relationship_type,
        )
        session.add(link)
        session.commit()
        session.refresh(link)
        return link

    def _looks_like_uuid(self, raw: str) -> bool:
        return bool(re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", raw))

    def _safe_history_log(self, raw: str | None) -> list[dict[str, Any]]:
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        normalized: list[dict[str, Any]] = []
        for item in parsed:
            if isinstance(item, dict):
                normalized.append(item)
        return normalized

    def _workspace_root(self) -> Path:
        return Path(__file__).resolve().parents[3] / "workspace"

    def _load_workspace_form_package(self, *, type_key: str) -> dict[str, Any] | None:
        workflow_path = self._workspace_root() / "forms" / type_key / "workflow.json"
        if not workflow_path.exists():
            return None
        try:
            raw = json.loads(workflow_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        return raw
