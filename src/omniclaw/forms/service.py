from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re
import shutil
from typing import Any

from fastapi import HTTPException

from omniclaw.db.enums import FormStatus, FormTypeLifecycle, NodeStatus
from omniclaw.db.models import FormLedger, FormTypeDefinition, Node
from omniclaw.db.repository import KernelRepository, TransitionConflictError
from omniclaw.forms.schemas import FormsActionRequest


class FormsService:
    _TYPE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
    _TARGET_VARIABLE_PATTERN = re.compile(r"^\{\{[a-zA-Z_][a-zA-Z0-9_]*\}\}$")
    _UUID_PATTERN = re.compile(
        r"^[0-9a-fA-F]{8}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{12}$"
    )

    def __init__(self, *, repository: KernelRepository) -> None:
        self._repository = repository

    def execute(self, request: FormsActionRequest) -> dict[str, object]:
        if request.action == "upsert_form_type":
            return self._upsert_form_type(request)
        if request.action == "validate_form_type":
            return self._validate_form_type(request)
        if request.action == "activate_form_type":
            return self._activate_form_type(request)
        if request.action == "deprecate_form_type":
            return self._deprecate_form_type(request)
        if request.action == "delete_form_type":
            return self._delete_form_type(request)
        if request.action == "list_form_types":
            return self._list_form_types(request)
        if request.action == "create_form":
            return self._create_form(request)
        if request.action == "transition_form":
            return self._transition_form(request)
        if request.action == "acknowledge_message_read":
            return self._acknowledge_message_read(request)
        raise HTTPException(status_code=400, detail=f"Unsupported forms action '{request.action}'")

    def sync_workspace_form_types(
        self,
        *,
        prune_missing: bool = False,
        activate: bool = True,
    ) -> dict[str, object]:
        forms_root = self._workspace_forms_root()
        if not forms_root.exists() or not forms_root.is_dir():
            raise HTTPException(status_code=400, detail=f"forms root not found: {forms_root}")

        workflow_paths = sorted(forms_root.glob("*/workflow.json"))
        synced_keys: set[tuple[str, str]] = set()
        items: list[dict[str, object]] = []
        removed: list[str] = []
        preserved: list[str] = []
        created = 0
        updated = 0
        unchanged = 0
        activated = 0
        failed = 0

        for workflow_path in workflow_paths:
            item: dict[str, object] = {"workflow_path": str(workflow_path.resolve())}
            try:
                workflow_graph = self._load_workspace_workflow_payload(workflow_path=workflow_path)
                type_key = str(workflow_graph.get("form_type") or workflow_path.parent.name).strip()
                version = str(workflow_graph.get("version") or "1.0.0").strip()
                if not type_key:
                    raise ValueError("missing form_type")
                if not version:
                    raise ValueError("missing version")

                normalized_graph = dict(workflow_graph)
                normalized_graph["form_type"] = type_key
                normalized_graph["version"] = version
                if self._is_stage_graph(normalized_graph):
                    normalized_graph = self._normalize_stage_graph_decisions(normalized_graph)

                raw_description = workflow_graph.get("description")
                description = raw_description.strip() if isinstance(raw_description, str) and raw_description.strip() else None
                raw_stage_metadata = workflow_graph.get("stage_metadata")
                stage_metadata = raw_stage_metadata if isinstance(raw_stage_metadata, dict) else {}

                validation_errors = self._validate_form_definition(
                    type_key=type_key,
                    workflow_graph=normalized_graph,
                    stage_metadata=stage_metadata,
                )
                if validation_errors:
                    item.update(
                        {
                            "status": "failed",
                            "type_key": type_key,
                            "version": version,
                            "errors": validation_errors,
                        }
                    )
                    failed += 1
                    items.append(item)
                    continue

                existing = self._repository.get_form_type_definition(type_key=type_key, version=version)
                is_changed = self._form_definition_changed(
                    existing=existing,
                    description=description,
                    workflow_graph=normalized_graph,
                    stage_metadata=stage_metadata,
                )

                if is_changed:
                    upserted = self.execute(
                        FormsActionRequest(
                            action="upsert_form_type",
                            type_key=type_key,
                            version=version,
                            description=description,
                            workflow_graph=normalized_graph,
                            stage_metadata=stage_metadata,
                        )
                    )
                    upsert_errors = upserted.get("validation_errors")
                    if isinstance(upsert_errors, list) and upsert_errors:
                        item.update(
                            {
                                "status": "failed",
                                "type_key": type_key,
                                "version": version,
                                "errors": [str(error) for error in upsert_errors],
                            }
                        )
                        failed += 1
                        items.append(item)
                        continue
                    if existing is None:
                        created += 1
                    else:
                        updated += 1
                else:
                    unchanged += 1

                lifecycle_state = existing.lifecycle_state.value if existing is not None else "DRAFT"
                if activate:
                    activated_definition = self.execute(
                        FormsActionRequest(
                            action="activate_form_type",
                            type_key=type_key,
                            version=version,
                        )
                    )
                    payload = activated_definition.get("form_type")
                    if isinstance(payload, dict):
                        lifecycle_state = str(payload.get("lifecycle_state") or lifecycle_state)
                    activated += 1

                synced_keys.add((type_key, version))
                item.update(
                    {
                        "status": "synced",
                        "type_key": type_key,
                        "version": version,
                        "changed": is_changed,
                        "lifecycle_state": lifecycle_state,
                    }
                )
                items.append(item)
            except (ValueError, OSError, HTTPException) as exc:
                item.update(
                    {
                        "status": "failed",
                        "errors": [str(exc)],
                    }
                )
                failed += 1
                items.append(item)

        if prune_missing:
            existing_definitions = self._repository.list_form_type_definitions()
            for definition in existing_definitions:
                key = (definition.type_key, definition.version)
                if key in synced_keys:
                    continue
                ref_count = self._repository.count_form_instances_for_type_version(
                    type_key=definition.type_key,
                    version=definition.version,
                )
                if ref_count > 0:
                    preserved.append(
                        f"{definition.type_key}@{definition.version} (referenced_by_forms={ref_count})"
                    )
                    continue
                self._repository.delete_form_type_definition(type_key=definition.type_key, version=definition.version)
                removed.append(f"{definition.type_key}@{definition.version}")

        return {
            "action": "sync_workspace_form_types",
            "summary": {
                "scanned": len(workflow_paths),
                "synced": len(synced_keys),
                "created": created,
                "updated": updated,
                "unchanged": unchanged,
                "activated": activated,
                "failed": failed,
                "removed": len(removed),
                "preserved": len(preserved),
            },
            "removed": sorted(removed),
            "preserved": sorted(preserved),
            "items": items,
        }

    def record_message_delivery(
        self,
        *,
        form_id_hint: str,
        sender_node_id: str,
        target_node_id: str,
        subject: str | None,
        message_name: str,
        source_path: str,
        delivery_path: str | None,
        archive_path: str | None,
    ) -> FormLedger:
        definition = self._resolve_message_form_definition()
        workflow_graph = self._decode_json(definition.workflow_graph)
        workflow_graph, _ = self._project_workflow_graph(
            workflow_graph=workflow_graph,
            stage_metadata={},
        )
        initial_status = self._message_initial_status(workflow_graph)
        dispatch_decision = self._message_dispatch_decision(workflow_graph)
        timestamp = datetime.now(timezone.utc)
        has_dispatch_edge = self._has_transition_edge(
            workflow_graph=workflow_graph,
            from_status=initial_status,
            decision_key=dispatch_decision,
        )
        initial_holder = sender_node_id if has_dispatch_edge else target_node_id

        created = self._repository.create_form_instance(
            form_id_hint=form_id_hint,
            form_type_key="message",
            form_type_version=definition.version,
            current_status=initial_status,
            current_holder_node=initial_holder,
            actor_node_id=sender_node_id,
            decision_key="create_draft",
            event_payload={"delivery_path": delivery_path, "archive_path": archive_path},
            message_name=message_name,
            sender_node_id=sender_node_id,
            target_node_id=target_node_id,
            subject=subject,
            source_path=source_path,
            delivery_path=delivery_path,
            archive_path=archive_path,
            dead_letter_path=None,
            queued_at=timestamp,
            routed_at=timestamp if not has_dispatch_edge else None,
            archived_at=None,
            dead_lettered_at=None,
            failure_reason=None,
            event_time=timestamp,
        )

        if not has_dispatch_edge:
            return created

        return self._transition_with_graph(
            form=created,
            definition=definition,
            decision_key=dispatch_decision,
            to_status=None,
            actor_node_id=sender_node_id,
            context={
                "sender_node_id": sender_node_id,
                "target_node_id": target_node_id,
            },
            payload={"delivery_path": delivery_path, "archive_path": archive_path},
            set_fields={"routed_at": timestamp},
            event_time=timestamp,
        )

    def _upsert_form_type(self, request: FormsActionRequest) -> dict[str, object]:
        type_key = self._require(request.type_key, "type_key")
        version = self._require(request.version, "version")
        workflow_graph = request.workflow_graph or {}
        if isinstance(workflow_graph, dict):
            workflow_graph = self._normalize_stage_graph_decisions(workflow_graph)
        stage_metadata = request.stage_metadata or {}
        lifecycle = self._parse_lifecycle(request.lifecycle_state or FormTypeLifecycle.DRAFT.value)

        self._validate_type_key(type_key)
        errors = self._validate_form_definition(type_key=type_key, workflow_graph=workflow_graph, stage_metadata=stage_metadata)
        if lifecycle == FormTypeLifecycle.ACTIVE and errors:
            raise HTTPException(status_code=400, detail={"errors": errors})
        if lifecycle == FormTypeLifecycle.ACTIVE and self._is_stage_graph(workflow_graph):
            distribution_errors = self._ensure_stage_graph_skill_distribution(
                type_key=type_key,
                workflow_graph=workflow_graph,
            )
            if distribution_errors:
                raise HTTPException(status_code=400, detail={"errors": distribution_errors})

        definition = self._repository.upsert_form_type_definition(
            type_key=type_key,
            version=version,
            lifecycle_state=lifecycle,
            workflow_graph=workflow_graph,
            stage_metadata=stage_metadata,
            description=request.description,
            validation_errors=errors if errors else None,
        )
        if lifecycle == FormTypeLifecycle.ACTIVE:
            definition = self._repository.set_form_type_lifecycle(
                type_key=type_key,
                version=version,
                lifecycle_state=FormTypeLifecycle.ACTIVE,
                validation_errors=None,
                deactivate_others=True,
            )
        self._persist_workflow_copy(
            type_key=type_key,
            version=version,
            description=request.description,
            workflow_graph=workflow_graph,
            stage_metadata=stage_metadata,
        )
        return {
            "action": request.action,
            "form_type": self._serialize_definition(definition),
            "validation_errors": errors,
        }

    def _validate_form_type(self, request: FormsActionRequest) -> dict[str, object]:
        type_key = self._require(request.type_key, "type_key")
        version = self._require(request.version, "version")
        definition = self._repository.get_form_type_definition(type_key=type_key, version=version)
        if definition is None:
            raise HTTPException(status_code=404, detail=f"form type '{type_key}' version '{version}' not found")

        graph = self._decode_json(definition.workflow_graph)
        stages = self._decode_json(definition.stage_metadata)
        errors = self._validate_form_definition(type_key=type_key, workflow_graph=graph, stage_metadata=stages)

        lifecycle = FormTypeLifecycle.VALIDATED if not errors else FormTypeLifecycle.DRAFT
        definition = self._repository.set_form_type_lifecycle(
            type_key=type_key,
            version=version,
            lifecycle_state=lifecycle,
            validation_errors=errors if errors else None,
        )
        return {
            "action": request.action,
            "valid": not errors,
            "errors": errors,
            "form_type": self._serialize_definition(definition),
        }

    def _activate_form_type(self, request: FormsActionRequest) -> dict[str, object]:
        type_key = self._require(request.type_key, "type_key")
        version = self._require(request.version, "version")
        definition = self._repository.get_form_type_definition(type_key=type_key, version=version)
        if definition is None:
            raise HTTPException(status_code=404, detail=f"form type '{type_key}' version '{version}' not found")

        graph = self._decode_json(definition.workflow_graph)
        stages = self._decode_json(definition.stage_metadata)
        errors = self._validate_form_definition(type_key=type_key, workflow_graph=graph, stage_metadata=stages)
        if errors:
            raise HTTPException(status_code=400, detail={"errors": errors})
        if self._is_stage_graph(graph):
            distribution_errors = self._ensure_stage_graph_skill_distribution(
                type_key=type_key,
                workflow_graph=graph,
            )
            if distribution_errors:
                raise HTTPException(status_code=400, detail={"errors": distribution_errors})

        definition = self._repository.set_form_type_lifecycle(
            type_key=type_key,
            version=version,
            lifecycle_state=FormTypeLifecycle.ACTIVE,
            deactivate_others=True,
            validation_errors=None,
        )
        self._persist_workflow_copy(
            type_key=type_key,
            version=version,
            description=definition.description,
            workflow_graph=graph,
            stage_metadata=stages if isinstance(stages, dict) else {},
        )
        return {
            "action": request.action,
            "form_type": self._serialize_definition(definition),
            "errors": [],
        }

    def _deprecate_form_type(self, request: FormsActionRequest) -> dict[str, object]:
        type_key = self._require(request.type_key, "type_key")
        version = self._require(request.version, "version")
        definition = self._repository.set_form_type_lifecycle(
            type_key=type_key,
            version=version,
            lifecycle_state=FormTypeLifecycle.DEPRECATED,
            validation_errors=None,
        )
        return {
            "action": request.action,
            "form_type": self._serialize_definition(definition),
        }

    def _delete_form_type(self, request: FormsActionRequest) -> dict[str, object]:
        type_key = self._require(request.type_key, "type_key")
        version = self._require(request.version, "version")
        deleted = self._repository.delete_form_type_definition(type_key=type_key, version=version)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"form type '{type_key}' version '{version}' not found")

        workflow_path = self._workspace_forms_root() / type_key / "workflow.json"
        if workflow_path.exists():
            try:
                raw = json.loads(workflow_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = {}
            if not isinstance(raw, dict) or str(raw.get("version") or "") == version:
                workflow_path.unlink(missing_ok=True)
        return {"action": request.action, "deleted": True, "type_key": type_key, "version": version}

    def _list_form_types(self, request: FormsActionRequest) -> dict[str, object]:
        definitions = self._repository.list_form_type_definitions(type_key=request.type_key)
        return {
            "action": request.action,
            "form_types": [self._serialize_definition(item) for item in definitions],
        }

    def _create_form(self, request: FormsActionRequest) -> dict[str, object]:
        type_key = self._require(request.type_key, "type_key")
        self._validate_type_key(type_key)

        if request.version:
            definition = self._repository.get_form_type_definition(type_key=type_key, version=request.version)
        else:
            definition = self._repository.get_form_type_definition(type_key=type_key, active_only=True)
        if definition is None:
            raise HTTPException(status_code=404, detail=f"active form type '{type_key}' not found")

        graph = self._decode_json(definition.workflow_graph)
        stages = self._decode_json(definition.stage_metadata)
        graph, _ = self._project_workflow_graph(
            workflow_graph=graph,
            stage_metadata=stages if isinstance(stages, dict) else {},
        )
        initial_status = request.initial_status or str(graph.get("initial_status") or "")
        if not initial_status:
            raise HTTPException(status_code=400, detail="initial status could not be resolved")

        holder_node_id = self._require(request.initial_holder_node_id, "initial_holder_node_id")
        self._require_node(holder_node_id)

        form = self._repository.create_form_instance(
            form_id_hint=request.form_id_hint or f"{type_key}-{initial_status}",
            form_type_key=type_key,
            form_type_version=definition.version,
            current_status=initial_status,
            current_holder_node=holder_node_id,
            actor_node_id=request.actor_node_id,
            decision_key=request.decision_key,
            event_payload=request.payload,
            message_name=None,
            sender_node_id=request.actor_node_id,
            target_node_id=None,
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
        return {
            "action": request.action,
            "form": self._serialize_form(form),
        }

    def _transition_form(self, request: FormsActionRequest) -> dict[str, object]:
        form_id = self._require(request.form_id, "form_id")
        actor_node_id = self._resolve_actor_node_id_from_request(request=request)
        current = self._repository.get_form_ledger(form_id=form_id)
        if current is None:
            raise HTTPException(status_code=404, detail=f"form '{form_id}' not found")
        if not current.form_type_key or not current.form_type_version:
            raise HTTPException(status_code=400, detail="form is missing type/version binding")
        if current.current_holder_node and current.current_holder_node != actor_node_id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "actor must match current form holder for decision: "
                    f"holder='{current.current_holder_node}' actor='{actor_node_id}'"
                ),
            )

        definition = self._repository.get_form_type_definition(
            type_key=current.form_type_key,
            version=current.form_type_version,
        )
        if definition is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "form type definition missing for "
                    f"'{current.form_type_key}' version '{current.form_type_version}'"
                ),
            )

        updated = self._transition_with_graph(
            form=current,
            definition=definition,
            decision_key=request.decision_key,
            to_status=request.to_status,
            actor_node_id=actor_node_id,
            context=request.context,
            payload=request.payload,
            set_fields=request.set_fields,
            event_time=datetime.now(timezone.utc),
        )
        return {
            "action": request.action,
            "form": self._serialize_form(updated),
        }

    def _acknowledge_message_read(self, request: FormsActionRequest) -> dict[str, object]:
        form_id = self._require(request.form_id, "form_id")
        actor_node_id = self._resolve_actor_node_id_from_request(request=request)

        current = self._repository.get_form_ledger(form_id=form_id)
        if current is None:
            raise HTTPException(status_code=404, detail=f"form '{form_id}' not found")
        if current.form_type_key != "message":
            raise HTTPException(status_code=400, detail="acknowledge_message_read supports only form type 'message'")
        if not current.current_holder_node:
            raise HTTPException(status_code=400, detail="form has no current holder")
        if current.current_holder_node != actor_node_id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "actor must match current form holder for read acknowledgement: "
                    f"holder='{current.current_holder_node}' actor='{actor_node_id}'"
                ),
            )

        if not current.form_type_version:
            raise HTTPException(status_code=400, detail="form is missing type/version binding")
        definition = self._repository.get_form_type_definition(
            type_key=current.form_type_key,
            version=current.form_type_version,
        )
        if definition is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "form type definition missing for "
                    f"'{current.form_type_key}' version '{current.form_type_version}'"
                ),
            )

        workflow_graph = self._decode_json(definition.workflow_graph)
        stages = self._decode_json(definition.stage_metadata)
        workflow_graph, _ = self._project_workflow_graph(
            workflow_graph=workflow_graph,
            stage_metadata=stages if isinstance(stages, dict) else {},
        )
        acknowledge_decision = request.decision_key or self._message_acknowledge_decision(workflow_graph)
        archive_status = self._message_archive_status(workflow_graph)
        event_payload = dict(request.payload or {})
        archive_copy_path = self._archive_message_read_copy(
            form=current,
            payload=event_payload,
        )
        if archive_copy_path is not None:
            event_payload["master_archive_copy_path"] = archive_copy_path

        now = datetime.now(timezone.utc)
        edge = self._resolve_edge(
            workflow_graph=workflow_graph,
            from_status=current.current_status,
            decision_key=acknowledge_decision,
            to_status=request.to_status,
        )
        resolved_holder = self._resolve_next_holder(
            form=current,
            edge=edge,
            actor_node_id=actor_node_id,
            context=request.context,
        )
        edge_to_status = str(edge.get("to") or "")
        set_fields = {"archived_at": now} if edge_to_status == archive_status else None
        try:
            updated = self._repository.transition_form_instance(
                form_id=current.form_id,
                expected_from_status=current.current_status,
                to_status=edge_to_status,
                new_holder_node_id=resolved_holder,
                actor_node_id=actor_node_id,
                decision_key=str(edge.get("decision") or ""),
                event_payload=event_payload,
                set_fields=set_fields,
                event_time=now,
            )
        except TransitionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "action": request.action,
            "form": self._serialize_form(updated),
        }

    def _archive_message_read_copy(
        self,
        *,
        form: FormLedger,
        payload: dict[str, Any],
    ) -> str | None:
        read_path_raw = payload.get("read_path")
        if not isinstance(read_path_raw, str) or not read_path_raw.strip():
            return None

        read_path = Path(read_path_raw).expanduser().resolve()
        if not read_path.exists() or not read_path.is_file():
            raise HTTPException(status_code=400, detail=f"read_path not found for archive copy: {read_path}")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive_dir = self._workspace_root() / "form_archive" / "message" / form.form_id
        archive_path = archive_dir / f"{timestamp}-ARCHIVED-{read_path.name}"
        try:
            archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(read_path, archive_path)
        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"failed to create master archive copy at '{archive_path}': {exc}",
            ) from exc
        return str(archive_path.resolve())

    def _transition_with_graph(
        self,
        *,
        form: FormLedger,
        definition: FormTypeDefinition,
        decision_key: str | None,
        to_status: str | None,
        actor_node_id: str | None,
        context: dict[str, Any],
        payload: dict[str, Any] | None,
        set_fields: dict[str, Any] | None,
        event_time: datetime,
    ) -> FormLedger:
        workflow_graph = self._decode_json(definition.workflow_graph)
        stages = self._decode_json(definition.stage_metadata)
        workflow_graph, _ = self._project_workflow_graph(
            workflow_graph=workflow_graph,
            stage_metadata=stages if isinstance(stages, dict) else {},
        )
        edge = self._resolve_edge(
            workflow_graph=workflow_graph,
            from_status=form.current_status,
            decision_key=decision_key,
            to_status=to_status,
        )
        resolved_holder = self._resolve_next_holder(
            form=form,
            edge=edge,
            actor_node_id=actor_node_id,
            context=context,
        )
        try:
            return self._repository.transition_form_instance(
                form_id=form.form_id,
                expected_from_status=form.current_status,
                to_status=str(edge.get("to") or ""),
                new_holder_node_id=resolved_holder,
                actor_node_id=actor_node_id,
                decision_key=str(edge.get("decision") or ""),
                event_payload=payload,
                set_fields=set_fields,
                event_time=event_time,
            )
        except TransitionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    def _resolve_edge(
        self,
        *,
        workflow_graph: dict[str, Any],
        from_status: str,
        decision_key: str | None,
        to_status: str | None,
    ) -> dict[str, Any]:
        raw_edges = workflow_graph.get("edges")
        if not isinstance(raw_edges, list):
            raise HTTPException(status_code=400, detail="workflow graph edges are invalid")

        candidates = [edge for edge in raw_edges if isinstance(edge, dict) and edge.get("from") == from_status]
        if decision_key is not None:
            candidates = [edge for edge in candidates if edge.get("decision") == decision_key]
        if to_status is not None:
            candidates = [edge for edge in candidates if edge.get("to") == to_status]

        if not candidates:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"no decision edge found from status '{from_status}'"
                    f" for decision '{decision_key}' and to_status '{to_status}'"
                ),
            )
        if len(candidates) > 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"ambiguous decision from status '{from_status}'"
                    "; specify to_status or decision_key more precisely"
                ),
            )
        return candidates[0]

    def _resolve_next_holder(
        self,
        *,
        form: FormLedger,
        edge: dict[str, Any],
        actor_node_id: str | None,
        context: dict[str, Any],
    ) -> str | None:
        holder_rule = edge.get("next_holder")
        if not isinstance(holder_rule, dict):
            raise HTTPException(status_code=400, detail="decision edge missing next_holder rule")

        strategy = str(holder_rule.get("strategy") or "")
        value = holder_rule.get("value")

        resolved: str | None
        if strategy == "none":
            resolved = None
        elif strategy == "static_node":
            resolved = str(value) if value is not None else None
        elif strategy == "static_node_name":
            if not isinstance(value, str) or not value.strip():
                raise HTTPException(status_code=400, detail="static_node_name strategy requires non-empty value")
            resolved = self._resolve_unique_node_id_by_name(value.strip())
        elif strategy == "field_ref":
            if not isinstance(value, str) or not value:
                raise HTTPException(status_code=400, detail="field_ref strategy requires non-empty value")
            field_value = context.get(value)
            resolved = str(field_value) if field_value is not None else None
        elif strategy == "previous_holder":
            resolved = form.current_holder_node
        elif strategy == "previous_actor":
            resolved = actor_node_id
        else:
            raise HTTPException(status_code=400, detail=f"unsupported next_holder strategy '{strategy}'")

        if resolved is not None:
            self._require_node(resolved)
        return resolved

    def _is_node_graph(self, workflow_graph: dict[str, Any]) -> bool:
        return isinstance(workflow_graph.get("nodes"), dict)

    def _is_stage_graph(self, workflow_graph: dict[str, Any]) -> bool:
        return isinstance(workflow_graph.get("stages"), dict)

    def _normalize_stage_graph_decisions(self, workflow_graph: dict[str, Any]) -> dict[str, Any]:
        if not self._is_stage_graph(workflow_graph):
            return workflow_graph

        normalized_graph = dict(workflow_graph)
        raw_stages = workflow_graph.get("stages")
        if not isinstance(raw_stages, dict):
            return normalized_graph

        normalized_stages: dict[str, Any] = {}
        for stage_name, stage_payload in raw_stages.items():
            if not isinstance(stage_payload, dict):
                normalized_stages[stage_name] = stage_payload
                continue

            normalized_stage = dict(stage_payload)
            decisions = stage_payload.get("decisions")
            legacy_transitions = stage_payload.get("transitions")

            if isinstance(decisions, dict):
                normalized_stage["decisions"] = dict(decisions)
            elif isinstance(legacy_transitions, dict):
                normalized_stage["decisions"] = dict(legacy_transitions)
            elif decisions is not None:
                normalized_stage["decisions"] = decisions
            elif legacy_transitions is not None:
                normalized_stage["decisions"] = legacy_transitions

            normalized_stage.pop("transitions", None)
            normalized_stages[stage_name] = normalized_stage

        normalized_graph["stages"] = normalized_stages
        return normalized_graph

    def _stage_decisions(self, stage_payload: dict[str, Any]) -> Any:
        decisions = stage_payload.get("decisions")
        if decisions is not None:
            return decisions
        return stage_payload.get("transitions")

    def _project_workflow_graph(
        self,
        *,
        workflow_graph: dict[str, Any],
        stage_metadata: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if self._is_stage_graph(workflow_graph):
            stages_raw = workflow_graph.get("stages")
            if not isinstance(stages_raw, dict):
                return workflow_graph, stage_metadata

            stage_names = [key for key in stages_raw.keys() if isinstance(key, str)]
            start_stage = workflow_graph.get("start_stage")
            if not isinstance(start_stage, str) or not start_stage.strip():
                start_stage = stage_names[0] if stage_names else None

            end_stage = self._infer_stage_graph_end_stage(workflow_graph=workflow_graph)
            projected_stage_metadata: dict[str, Any] = {}
            projected_edges: list[dict[str, Any]] = []

            for stage_name, stage_payload in stages_raw.items():
                if not isinstance(stage_name, str) or not isinstance(stage_payload, dict):
                    continue

                required_skill = stage_payload.get("required_skill")
                if isinstance(required_skill, str) and required_skill.strip():
                    projected_stage_metadata[stage_name] = {"stage_skill_ref": required_skill.strip()}

                decisions = self._stage_decisions(stage_payload)
                if not isinstance(decisions, dict):
                    continue
                for decision, next_stage in decisions.items():
                    if not isinstance(decision, str) or not decision.strip():
                        continue
                    if not isinstance(next_stage, str) or not next_stage.strip():
                        continue
                    target_stage_payload = stages_raw.get(next_stage)
                    target_rule = None
                    if isinstance(target_stage_payload, dict):
                        target_rule = target_stage_payload.get("target")
                    projected_edges.append(
                        {
                            "from": stage_name,
                            "to": next_stage,
                            "decision": decision.strip(),
                            "next_holder": self._holder_rule_from_stage_target(target_rule),
                        }
                    )

            projected_graph: dict[str, Any] = {
                "initial_status": start_stage,
                "edges": projected_edges,
                "dispatch_decision": workflow_graph.get("dispatch_decision"),
                "acknowledge_decision": workflow_graph.get("acknowledge_decision"),
                "archive_status": workflow_graph.get("archive_status") or end_stage,
                "end_status": end_stage,
            }
            return projected_graph, projected_stage_metadata

        if not self._is_node_graph(workflow_graph):
            return workflow_graph, stage_metadata

        nodes_raw = workflow_graph.get("nodes")
        edges_raw = workflow_graph.get("edges")
        if not isinstance(nodes_raw, dict):
            return workflow_graph, stage_metadata

        status_by_node_key: dict[str, str] = {}
        projected_stage_metadata: dict[str, Any] = {}
        for node_key, node in nodes_raw.items():
            if not isinstance(node_key, str) or not isinstance(node, dict):
                continue
            status = node.get("status")
            if not isinstance(status, str) or not status.strip():
                continue
            normalized_status = status.strip()
            status_by_node_key[node_key] = normalized_status
            stage_skill_ref = node.get("stage_skill_ref")
            if isinstance(stage_skill_ref, str) and stage_skill_ref.strip():
                projected_stage_metadata[normalized_status] = {
                    "stage_skill_ref": stage_skill_ref.strip(),
                }

        projected_edges: list[dict[str, Any]] = []
        if isinstance(edges_raw, list):
            for edge in edges_raw:
                if not isinstance(edge, dict):
                    continue
                from_node = edge.get("from")
                to_node = edge.get("to")
                if not isinstance(from_node, str) or not isinstance(to_node, str):
                    continue
                from_status = status_by_node_key.get(from_node)
                to_status = status_by_node_key.get(to_node)
                if from_status is None or to_status is None:
                    continue
                next_holder = None
                to_node_payload = nodes_raw.get(to_node)
                if isinstance(to_node_payload, dict):
                    next_holder = to_node_payload.get("holder")
                if not isinstance(next_holder, dict):
                    next_holder = edge.get("next_holder")
                projected_edges.append(
                    {
                        "from": from_status,
                        "to": to_status,
                        "decision": edge.get("decision"),
                        "next_holder": next_holder,
                    }
                )

        start_node = workflow_graph.get("start_node")
        end_node = workflow_graph.get("end_node")
        initial_status = status_by_node_key.get(start_node) if isinstance(start_node, str) else None
        end_status = status_by_node_key.get(end_node) if isinstance(end_node, str) else None

        projected_graph: dict[str, Any] = {
            "initial_status": initial_status,
            "edges": projected_edges,
            "dispatch_decision": workflow_graph.get("dispatch_decision"),
            "acknowledge_decision": workflow_graph.get("acknowledge_decision"),
            "archive_status": workflow_graph.get("archive_status") or end_status,
            "end_status": end_status,
        }
        return projected_graph, projected_stage_metadata

    def _holder_rule_from_stage_target(self, target_value: Any) -> dict[str, Any]:
        if not isinstance(target_value, str) or not target_value.strip():
            return {"strategy": "none"}

        target = target_value.strip()
        if target.lower() in {"none", "null", "{{none}}"}:
            return {"strategy": "none"}
        if target == "{{initiator}}":
            return {"strategy": "field_ref", "value": "initiator_node_id"}
        if target == "{{any}}":
            return {"strategy": "field_ref", "value": "target_node_id"}

        var_match = re.fullmatch(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}", target)
        if var_match:
            variable_name = var_match.group(1)
            return {"strategy": "field_ref", "value": f"{variable_name}_node_id"}

        if self._UUID_PATTERN.fullmatch(target):
            return {"strategy": "static_node", "value": target}

        return {"strategy": "static_node_name", "value": target}

    def _infer_stage_graph_end_stage(self, *, workflow_graph: dict[str, Any]) -> str | None:
        end_stage = workflow_graph.get("end_stage")
        if isinstance(end_stage, str) and end_stage.strip():
            return end_stage.strip()

        stages_raw = workflow_graph.get("stages")
        if not isinstance(stages_raw, dict):
            return None
        for stage_name, stage_payload in stages_raw.items():
            if not isinstance(stage_name, str) or not isinstance(stage_payload, dict):
                continue
            if stage_payload.get("is_terminal") is True:
                return stage_name
        return None

    def _validate_holder_rule(self, *, holder: Any, path: str, errors: list[str]) -> None:
        if not isinstance(holder, dict):
            errors.append(f"{path} is required")
            return

        strategy = holder.get("strategy")
        if strategy not in {
            "none",
            "static_node",
            "static_node_name",
            "field_ref",
            "previous_holder",
            "previous_actor",
        }:
            errors.append(f"{path}.strategy is invalid")
            return

        if strategy in {"static_node", "static_node_name", "field_ref"}:
            holder_value = holder.get("value")
            if not isinstance(holder_value, str) or not holder_value.strip():
                errors.append(f"{path}.value is required for strategy '{strategy}'")

    def _validate_node_graph_definition(
        self,
        *,
        workflow_graph: dict[str, Any],
    ) -> list[str]:
        errors: list[str] = []

        raw_nodes = workflow_graph.get("nodes")
        if not isinstance(raw_nodes, dict) or not raw_nodes:
            errors.append("workflow_graph.nodes must be a non-empty object")
            raw_nodes = {}

        start_node = workflow_graph.get("start_node")
        if not isinstance(start_node, str) or not start_node.strip():
            errors.append("workflow_graph.start_node is required")

        end_node = workflow_graph.get("end_node")
        if not isinstance(end_node, str) or not end_node.strip():
            errors.append("workflow_graph.end_node is required")

        seen_statuses: set[str] = set()
        legacy_nodes: set[str] = set()

        for node_key, node_payload in raw_nodes.items():
            if not isinstance(node_key, str) or not node_key.strip():
                errors.append("workflow_graph.nodes keys must be non-empty strings")
                continue
            if not isinstance(node_payload, dict):
                errors.append(f"workflow_graph.nodes['{node_key}'] must be an object")
                continue

            if node_payload.get("legacy_compat") is True:
                legacy_nodes.add(node_key)

            status = node_payload.get("status")
            if not isinstance(status, str) or not status.strip():
                errors.append(f"workflow_graph.nodes['{node_key}'].status is required")
            else:
                normalized_status = status.strip()
                if normalized_status in seen_statuses:
                    errors.append(
                        "workflow_graph.nodes statuses must be unique; "
                        f"duplicate status '{normalized_status}'"
                    )
                seen_statuses.add(normalized_status)

            stage_skill_ref = node_payload.get("stage_skill_ref")
            if not isinstance(stage_skill_ref, str) or not stage_skill_ref.strip():
                errors.append(f"workflow_graph.nodes['{node_key}'].stage_skill_ref is required")

            self._validate_holder_rule(
                holder=node_payload.get("holder"),
                path=f"workflow_graph.nodes['{node_key}'].holder",
                errors=errors,
            )

        if isinstance(start_node, str) and start_node and start_node not in raw_nodes:
            errors.append(f"workflow_graph.start_node '{start_node}' is not defined in workflow_graph.nodes")
        if isinstance(end_node, str) and end_node and end_node not in raw_nodes:
            errors.append(f"workflow_graph.end_node '{end_node}' is not defined in workflow_graph.nodes")

        raw_edges = workflow_graph.get("edges")
        if not isinstance(raw_edges, list) or not raw_edges:
            errors.append("workflow_graph.edges must be a non-empty list")
            raw_edges = []

        seen_pairs: set[tuple[str, str]] = set()
        adjacency: dict[str, set[str]] = {}
        for index, edge in enumerate(raw_edges):
            if not isinstance(edge, dict):
                errors.append(f"workflow_graph.edges[{index}] must be an object")
                continue

            from_node = edge.get("from")
            to_node = edge.get("to")
            decision = edge.get("decision")
            if not isinstance(from_node, str) or not from_node.strip():
                errors.append(f"workflow_graph.edges[{index}].from is required")
                continue
            if not isinstance(to_node, str) or not to_node.strip():
                errors.append(f"workflow_graph.edges[{index}].to is required")
                continue
            if not isinstance(decision, str) or not decision.strip():
                errors.append(f"workflow_graph.edges[{index}].decision is required")
                continue

            if from_node not in raw_nodes:
                errors.append(f"workflow_graph.edges[{index}].from '{from_node}' is not a defined node")
            if to_node not in raw_nodes:
                errors.append(f"workflow_graph.edges[{index}].to '{to_node}' is not a defined node")

            pair = (from_node, decision.strip())
            if pair in seen_pairs:
                errors.append(
                    "workflow_graph edges must be unique by (from, decision); "
                    f"duplicate found for ({from_node}, {decision.strip()})"
                )
            seen_pairs.add(pair)
            adjacency.setdefault(from_node, set()).add(to_node)

            if isinstance(end_node, str) and from_node == end_node:
                errors.append("workflow_graph.end_node must not have outgoing edges")

        acknowledge_decision = workflow_graph.get("acknowledge_decision")
        if acknowledge_decision is not None and (
            not isinstance(acknowledge_decision, str) or not acknowledge_decision.strip()
        ):
            errors.append("workflow_graph.acknowledge_decision must be a non-empty string when provided")

        dispatch_decision = workflow_graph.get("dispatch_decision")
        if dispatch_decision is not None and (
            not isinstance(dispatch_decision, str) or not dispatch_decision.strip()
        ):
            errors.append("workflow_graph.dispatch_decision must be a non-empty string when provided")

        archive_status = workflow_graph.get("archive_status")
        if archive_status is not None and (not isinstance(archive_status, str) or not archive_status.strip()):
            errors.append("workflow_graph.archive_status must be a non-empty string when provided")

        if not errors and isinstance(start_node, str) and isinstance(end_node, str):
            reachable = {start_node}
            stack = [start_node]
            while stack:
                node = stack.pop()
                for nxt in adjacency.get(node, set()):
                    if nxt not in reachable:
                        reachable.add(nxt)
                        stack.append(nxt)

            ignored = {node_key for node_key in legacy_nodes if node_key in raw_nodes}
            all_nodes = set(raw_nodes.keys()) - ignored
            unreachable = sorted(all_nodes - reachable)
            if unreachable:
                errors.append(f"unreachable workflow nodes: {', '.join(unreachable)}")
            if end_node not in reachable:
                errors.append(f"workflow_graph.end_node '{end_node}' is not reachable from start_node")

        return errors

    def _validate_stage_graph_definition(
        self,
        *,
        type_key: str,
        workflow_graph: dict[str, Any],
    ) -> list[str]:
        errors: list[str] = []

        declared_form_type = workflow_graph.get("form_type")
        if declared_form_type is not None and declared_form_type != type_key:
            errors.append(
                f"workflow_graph.form_type '{declared_form_type}' must match type_key '{type_key}'"
            )

        raw_stages = workflow_graph.get("stages")
        if not isinstance(raw_stages, dict) or not raw_stages:
            errors.append("workflow_graph.stages must be a non-empty object")
            raw_stages = {}

        stage_names = [name for name in raw_stages.keys() if isinstance(name, str) and name.strip()]
        start_stage = workflow_graph.get("start_stage")
        if start_stage is None and stage_names:
            start_stage = stage_names[0]
        if not isinstance(start_stage, str) or not start_stage.strip():
            errors.append("workflow_graph.start_stage is required")
            start_stage = None
        elif start_stage not in raw_stages:
            errors.append(f"workflow_graph.start_stage '{start_stage}' is not defined in workflow_graph.stages")

        end_stage = workflow_graph.get("end_stage")
        if not isinstance(end_stage, str) or not end_stage.strip():
            errors.append("workflow_graph.end_stage is required")
            end_stage = None
        elif end_stage not in raw_stages:
            errors.append(f"workflow_graph.end_stage '{end_stage}' is not defined in workflow_graph.stages")

        seen_pairs: set[tuple[str, str]] = set()
        adjacency: dict[str, set[str]] = {}
        required_skills: set[str] = set()

        for stage_name, stage_payload in raw_stages.items():
            if not isinstance(stage_name, str) or not stage_name.strip():
                errors.append("workflow_graph.stages keys must be non-empty strings")
                continue
            if not isinstance(stage_payload, dict):
                errors.append(f"workflow_graph.stages['{stage_name}'] must be an object")
                continue

            is_terminal = stage_payload.get("is_terminal") is True
            target = stage_payload.get("target")
            target_is_none = False
            if target is None:
                target_is_none = True
            elif not isinstance(target, str) or not target.strip():
                errors.append(
                    f"workflow_graph.stages['{stage_name}'].target must be a non-empty string or null"
                )
            else:
                target = target.strip()
                normalized_target = target.lower()
                if normalized_target in {"none", "null", "{{none}}"}:
                    target_is_none = True

            if not is_terminal and target_is_none:
                errors.append(
                    f"workflow_graph.stages['{stage_name}'].target is required for non-terminal stage"
                )
            if isinstance(target, str) and target and not target_is_none and not self._is_dynamic_target(target):
                _, node_error = self._resolve_node_reference(target)
                if node_error is not None:
                    errors.append(
                        f"workflow_graph.stages['{stage_name}'].target invalid: {node_error}"
                    )

            required_skill = stage_payload.get("required_skill")
            required_skill_str = required_skill.strip() if isinstance(required_skill, str) else None
            requires_skill = (not is_terminal) or (not target_is_none)
            if requires_skill:
                if not required_skill_str:
                    errors.append(
                        f"workflow_graph.stages['{stage_name}'].required_skill is required "
                        "(non-terminal stage or terminal stage with holder target)"
                    )
                else:
                    required_skills.add(required_skill_str)
            elif required_skill is not None:
                if not required_skill_str:
                    errors.append(
                        f"workflow_graph.stages['{stage_name}'].required_skill must be non-empty when provided"
                    )
                else:
                    required_skills.add(required_skill_str)

            decisions = self._stage_decisions(stage_payload)
            if decisions is None:
                decisions = {}
            if not isinstance(decisions, dict):
                errors.append(f"workflow_graph.stages['{stage_name}'].decisions must be an object")
                decisions = {}
            if not is_terminal and not decisions:
                errors.append(
                    f"workflow_graph.stages['{stage_name}'] requires non-empty decisions unless is_terminal=true"
                )
            if is_terminal and decisions:
                errors.append(
                    f"workflow_graph.stages['{stage_name}'] is terminal and must not declare decisions"
                )

            for decision, next_stage in decisions.items():
                if not isinstance(decision, str) or not decision.strip():
                    errors.append(
                        f"workflow_graph.stages['{stage_name}'].decisions contains empty decision key"
                    )
                    continue
                if not isinstance(next_stage, str) or not next_stage.strip():
                    errors.append(
                        f"workflow_graph.stages['{stage_name}'].decisions['{decision}'] target is required"
                    )
                    continue
                if next_stage not in raw_stages:
                    errors.append(
                        f"workflow_graph.stages['{stage_name}'].decisions['{decision}'] "
                        f"references unknown stage '{next_stage}'"
                    )
                pair = (stage_name, decision.strip())
                if pair in seen_pairs:
                    errors.append(
                        "workflow_graph decisions must be unique by (stage, decision); "
                        f"duplicate found for ({stage_name}, {decision.strip()})"
                    )
                seen_pairs.add(pair)
                adjacency.setdefault(stage_name, set()).add(next_stage)

        if end_stage and end_stage in adjacency and adjacency.get(end_stage):
            errors.append("workflow_graph.end_stage must not have outgoing decisions")

        if not errors and start_stage and end_stage:
            reachable = {start_stage}
            stack = [start_stage]
            while stack:
                stage = stack.pop()
                for nxt in adjacency.get(stage, set()):
                    if nxt not in reachable:
                        reachable.add(nxt)
                        stack.append(nxt)
            unreachable = sorted(set(raw_stages.keys()) - reachable)
            if unreachable:
                errors.append(f"unreachable workflow stages: {', '.join(unreachable)}")
            if end_stage not in reachable:
                errors.append(f"workflow_graph.end_stage '{end_stage}' is not reachable from start_stage")

        errors.extend(self._validate_initiator_allowlist(workflow_graph=workflow_graph))

        forms_root = self._workspace_form_skills_root(type_key=type_key)
        for skill_name in sorted(required_skills):
            skill_file = forms_root / skill_name / "SKILL.md"
            if not skill_file.exists():
                errors.append(
                    f"required skill '{skill_name}' missing at {skill_file}"
                )

        return errors

    def _ensure_stage_graph_skill_distribution(
        self,
        *,
        type_key: str,
        workflow_graph: dict[str, Any],
    ) -> list[str]:
        raw_stages = workflow_graph.get("stages")
        if not isinstance(raw_stages, dict):
            return ["workflow_graph.stages must be a non-empty object"]

        errors: list[str] = []
        active_agent_nodes = self._repository.list_active_agent_nodes_with_workspaces()
        active_workspace_nodes = [
            node
            for node in self._repository.list_nodes_with_workspaces()
            if node.status == NodeStatus.ACTIVE
        ]
        initiator_allowlist_nodes, initiator_allowlist_errors = self._resolve_initiator_allowlist_nodes(
            workflow_graph=workflow_graph,
            active_workspace_nodes=active_workspace_nodes,
        )
        errors.extend(initiator_allowlist_errors)

        for stage_name, stage_payload in raw_stages.items():
            if not isinstance(stage_name, str) or not stage_name.strip():
                continue
            if not isinstance(stage_payload, dict):
                continue

            required_skill_raw = stage_payload.get("required_skill")
            required_skill = required_skill_raw.strip() if isinstance(required_skill_raw, str) else ""
            if not required_skill:
                continue

            skill_source_dir = self._workspace_form_skills_root(type_key=type_key) / required_skill
            skill_file = skill_source_dir / "SKILL.md"
            if not skill_file.exists():
                errors.append(
                    f"workflow_graph.stages['{stage_name}'].required_skill '{required_skill}' missing at {skill_file}"
                )
                continue

            skill_manifest_defaults = self._load_skill_manifest_defaults(
                skill_source_dir=skill_source_dir,
                skill_name=required_skill,
            )
            try:
                self._repository.upsert_master_skill(
                    name=skill_manifest_defaults["name"],
                    form_type_key=type_key,
                    master_path=str(skill_source_dir.resolve()),
                    description=skill_manifest_defaults["description"],
                    version=skill_manifest_defaults["version"],
                )
            except ValueError as exc:
                errors.append(
                    f"failed cataloging master skill '{required_skill}' for form '{type_key}': {exc}"
                )
                continue

            target_nodes, target_error = self._resolve_stage_distribution_nodes(
                stage_name=stage_name,
                stage_payload=stage_payload,
                active_agent_nodes=active_agent_nodes,
                active_workspace_nodes=active_workspace_nodes,
                initiator_allowlist_nodes=initiator_allowlist_nodes,
            )
            if target_error is not None:
                errors.append(target_error)
                continue

            for node in target_nodes:
                distribution_error = self._copy_skill_to_node(
                    node=node,
                    skill_name=required_skill,
                    skill_source_dir=skill_source_dir,
                    manifest_defaults=skill_manifest_defaults,
                )
                if distribution_error is not None:
                    errors.append(distribution_error)
        return errors

    def _resolve_stage_distribution_nodes(
        self,
        *,
        stage_name: str,
        stage_payload: dict[str, Any],
        active_agent_nodes: list[Node],
        active_workspace_nodes: list[Node],
        initiator_allowlist_nodes: list[Node] | None,
    ) -> tuple[list[Node], str | None]:
        target = stage_payload.get("target")
        if target is None:
            return [], None
        if not isinstance(target, str) or not target.strip():
            return [], (
                f"workflow_graph.stages['{stage_name}'].target must be a non-empty string or null"
            )
        target = target.strip()
        if target.lower() in {"none", "null", "{{none}}"}:
            return [], None

        if target == "{{any}}":
            return active_agent_nodes, None
        if target == "{{initiator}}":
            if initiator_allowlist_nodes is not None:
                return initiator_allowlist_nodes, None
            return active_workspace_nodes, None
        if self._is_dynamic_target(target):
            return active_agent_nodes, None

        node, node_error = self._resolve_node_reference(target)
        if node_error is not None or node is None:
            not_found_reason = node_error if node_error is not None else f"node '{target}' not found"
            return [], (
                f"workflow_graph.stages['{stage_name}'].target invalid: "
                f"{not_found_reason}"
            )
        return [node], None

    def _validate_initiator_allowlist(self, *, workflow_graph: dict[str, Any]) -> list[str]:
        raw_allowlist = workflow_graph.get("initiator_allowlist")
        if raw_allowlist is None:
            return []

        errors: list[str] = []
        if not isinstance(raw_allowlist, list) or not raw_allowlist:
            return ["workflow_graph.initiator_allowlist must be a non-empty array when provided"]

        for index, raw_reference in enumerate(raw_allowlist):
            if not isinstance(raw_reference, str) or not raw_reference.strip():
                errors.append(
                    f"workflow_graph.initiator_allowlist[{index}] must be a non-empty node name/id or '{{{{any}}}}'"
                )
                continue
            reference = raw_reference.strip()
            if reference == "{{any}}":
                continue
            _, node_error = self._resolve_node_reference(reference)
            if node_error is not None:
                errors.append(f"workflow_graph.initiator_allowlist[{index}] invalid: {node_error}")
        return errors

    def _resolve_initiator_allowlist_nodes(
        self,
        *,
        workflow_graph: dict[str, Any],
        active_workspace_nodes: list[Node],
    ) -> tuple[list[Node] | None, list[str]]:
        raw_allowlist = workflow_graph.get("initiator_allowlist")
        if raw_allowlist is None:
            return None, []
        if not isinstance(raw_allowlist, list) or not raw_allowlist:
            return None, ["workflow_graph.initiator_allowlist must be a non-empty array when provided"]

        errors: list[str] = []
        active_nodes_by_id = {node.id: node for node in active_workspace_nodes}
        selected: dict[str, Node] = {}

        for index, raw_reference in enumerate(raw_allowlist):
            if not isinstance(raw_reference, str) or not raw_reference.strip():
                errors.append(
                    f"workflow_graph.initiator_allowlist[{index}] must be a non-empty node name/id or '{{{{any}}}}'"
                )
                continue
            reference = raw_reference.strip()
            if reference == "{{any}}":
                return active_workspace_nodes, errors

            node, node_error = self._resolve_node_reference(reference)
            if node_error is not None or node is None:
                reason = node_error if node_error is not None else f"node '{reference}' not found"
                errors.append(f"workflow_graph.initiator_allowlist[{index}] invalid: {reason}")
                continue

            active_workspace_node = active_nodes_by_id.get(node.id)
            if active_workspace_node is None:
                errors.append(
                    f"workflow_graph.initiator_allowlist[{index}] node '{node.name}' is not ACTIVE with workspace_root"
                )
                continue
            selected[active_workspace_node.id] = active_workspace_node

        if errors:
            return None, errors
        return list(selected.values()), []

    def _copy_skill_to_node(
        self,
        *,
        node: Node,
        skill_name: str,
        skill_source_dir: Path,
        manifest_defaults: dict[str, str],
    ) -> str | None:
        workspace_root = node.workspace_root
        if not isinstance(workspace_root, str) or not workspace_root.strip():
            return (
                f"node '{node.name}' has no workspace_root; "
                f"cannot distribute required_skill '{skill_name}'"
            )

        workspace = Path(workspace_root).expanduser().resolve()
        target_skill_dir = workspace / "skills" / skill_name
        try:
            if target_skill_dir.exists():
                if target_skill_dir.is_dir():
                    shutil.rmtree(target_skill_dir)
                else:
                    target_skill_dir.unlink()
            target_skill_dir.mkdir(parents=True, exist_ok=True)
            for child in skill_source_dir.iterdir():
                destination = target_skill_dir / child.name
                if child.is_dir():
                    shutil.copytree(child, destination, dirs_exist_ok=True)
                else:
                    shutil.copy2(child, destination)
            manifest_error = self._ensure_skill_manifest(
                target_skill_dir=target_skill_dir,
                skill_name=skill_name,
                manifest_defaults=manifest_defaults,
            )
            if manifest_error is not None:
                return (
                    f"failed writing skill.json for required_skill '{skill_name}' "
                    f"to node '{node.name}' at '{target_skill_dir}': {manifest_error}"
                )
        except OSError as exc:
            return (
                f"failed distributing required_skill '{skill_name}' to node '{node.name}' "
                f"at '{target_skill_dir}': {exc}"
            )
        return None

    def _ensure_skill_manifest(
        self,
        *,
        target_skill_dir: Path,
        skill_name: str,
        manifest_defaults: dict[str, str],
    ) -> str | None:
        manifest_path = target_skill_dir / "skill.json"
        payload: dict[str, Any] = {}
        if manifest_path.exists():
            try:
                existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                return str(exc)
            if isinstance(existing, dict):
                payload.update(existing)

        defaults = {
            "name": manifest_defaults.get("name", skill_name),
            "version": manifest_defaults.get("version", "1.0.0"),
            "description": manifest_defaults.get(
                "description",
                f"Dispatched form skill package '{skill_name}'.",
            ),
            "author": manifest_defaults.get("author", "omniclaw-kernel"),
        }
        for key, value in defaults.items():
            if key == "description":
                payload[key] = value
                continue
            existing_value = payload.get(key)
            if not isinstance(existing_value, str) or not existing_value.strip():
                payload[key] = value

        try:
            manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            return str(exc)
        return None

    def _load_skill_manifest_defaults(self, *, skill_source_dir: Path, skill_name: str) -> dict[str, str]:
        defaults = {
            "name": skill_name,
            "version": "1.0.0",
            "description": f"Dispatched form skill package '{skill_name}'.",
            "author": "omniclaw-kernel",
        }

        source_manifest_path = skill_source_dir / "skill.json"
        if source_manifest_path.exists():
            try:
                source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                source_manifest = {}
            if isinstance(source_manifest, dict):
                for key in ("name", "version", "description", "author"):
                    raw_value = source_manifest.get(key)
                    if isinstance(raw_value, str) and raw_value.strip():
                        defaults[key] = raw_value.strip()

        frontmatter = self._parse_skill_frontmatter(skill_source_dir / "SKILL.md")
        name = self._optional_str(frontmatter.get("name"))
        description = self._optional_str(frontmatter.get("description"))
        version = self._optional_str(frontmatter.get("version"))
        author = self._optional_str(frontmatter.get("author"))
        if name:
            defaults["name"] = name
        if description:
            defaults["description"] = description
        if version:
            defaults["version"] = version
        if author:
            defaults["author"] = author
        return defaults

    def _parse_skill_frontmatter(self, skill_path: Path) -> dict[str, str]:
        try:
            content = skill_path.read_text(encoding="utf-8")
        except OSError:
            return {}

        if not content.startswith("---\n"):
            return {}
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}

        closing_index: int | None = None
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                closing_index = index
                break
        if closing_index is None:
            return {}

        frontmatter: dict[str, str] = {}
        for line in lines[1:closing_index]:
            stripped = line.strip()
            if not stripped or ":" not in stripped:
                continue
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                frontmatter[key] = value
        return frontmatter

    def _is_dynamic_target(self, target: str) -> bool:
        if target in {"{{initiator}}", "{{any}}"}:
            return True
        return self._TARGET_VARIABLE_PATTERN.fullmatch(target) is not None

    def _resolve_node_reference(self, value: str) -> tuple[Node | None, str | None]:
        return self._repository.resolve_unique_node_reference(value)

    def _validate_form_definition(
        self,
        *,
        type_key: str,
        workflow_graph: dict[str, Any],
        stage_metadata: dict[str, Any],
    ) -> list[str]:
        if self._is_stage_graph(workflow_graph):
            errors: list[str] = []
            try:
                self._validate_type_key(type_key)
            except HTTPException as exc:
                errors.append(str(exc.detail))
            errors.extend(
                self._validate_stage_graph_definition(
                    type_key=type_key,
                    workflow_graph=workflow_graph,
                )
            )
            return errors

        if self._is_node_graph(workflow_graph):
            errors: list[str] = []
            try:
                self._validate_type_key(type_key)
            except HTTPException as exc:
                errors.append(str(exc.detail))
            errors.extend(self._validate_node_graph_definition(workflow_graph=workflow_graph))
            return errors

        return self._validate_legacy_form_definition(
            type_key=type_key,
            workflow_graph=workflow_graph,
            stage_metadata=stage_metadata,
        )

    def _validate_legacy_form_definition(
        self,
        *,
        type_key: str,
        workflow_graph: dict[str, Any],
        stage_metadata: dict[str, Any],
    ) -> list[str]:
        errors: list[str] = []
        try:
            self._validate_type_key(type_key)
        except HTTPException as exc:
            errors.append(str(exc.detail))

        initial_status = workflow_graph.get("initial_status")
        if not isinstance(initial_status, str) or not initial_status.strip():
            errors.append("workflow_graph.initial_status is required")

        raw_edges = workflow_graph.get("edges")
        if not isinstance(raw_edges, list) or not raw_edges:
            errors.append("workflow_graph.edges must be a non-empty list")
            raw_edges = []

        seen_pairs: set[tuple[str, str]] = set()
        statuses: set[str] = set()
        workflow_statuses: set[str] = set()
        adjacency: dict[str, set[str]] = {}

        for index, edge in enumerate(raw_edges):
            if not isinstance(edge, dict):
                errors.append(f"workflow_graph.edges[{index}] must be an object")
                continue

            from_status = edge.get("from")
            to_status = edge.get("to")
            decision = str(edge.get("decision") or "")
            if not isinstance(from_status, str) or not from_status:
                errors.append(f"workflow_graph.edges[{index}].from is required")
                continue
            if not isinstance(to_status, str) or not to_status:
                errors.append(f"workflow_graph.edges[{index}].to is required")
                continue

            pair = (from_status, decision)
            if pair in seen_pairs:
                errors.append(
                    "workflow_graph edges must be unique by (from, decision); "
                    f"duplicate found for ({from_status}, {decision or '<default>'})"
                )
            seen_pairs.add(pair)

            statuses.add(from_status)
            statuses.add(to_status)
            workflow_statuses.add(from_status)
            workflow_statuses.add(to_status)
            adjacency.setdefault(from_status, set()).add(to_status)

            holder = edge.get("next_holder")
            if not isinstance(holder, dict):
                errors.append(f"workflow_graph.edges[{index}].next_holder is required")
                continue
            strategy = holder.get("strategy")
            if strategy not in {
                "none",
                "static_node",
                "static_node_name",
                "field_ref",
                "previous_holder",
                "previous_actor",
            }:
                errors.append(f"workflow_graph.edges[{index}].next_holder.strategy is invalid")
            if strategy in {"static_node", "static_node_name", "field_ref"}:
                holder_value = holder.get("value")
                if not isinstance(holder_value, str) or not holder_value.strip():
                    errors.append(
                        f"workflow_graph.edges[{index}].next_holder.value is required for strategy '{strategy}'"
                    )

        if isinstance(initial_status, str) and initial_status:
            statuses.add(initial_status)
            workflow_statuses.add(initial_status)

        if not isinstance(stage_metadata, dict):
            errors.append("stage_metadata must be an object")
        else:
            acknowledge_decision = workflow_graph.get("acknowledge_decision")
            if acknowledge_decision is not None and (
                not isinstance(acknowledge_decision, str) or not acknowledge_decision.strip()
            ):
                errors.append("workflow_graph.acknowledge_decision must be a non-empty string when provided")

            dispatch_decision = workflow_graph.get("dispatch_decision")
            if dispatch_decision is not None and (
                not isinstance(dispatch_decision, str) or not dispatch_decision.strip()
            ):
                errors.append("workflow_graph.dispatch_decision must be a non-empty string when provided")

            archive_status = workflow_graph.get("archive_status")
            if archive_status is not None:
                if not isinstance(archive_status, str) or not archive_status.strip():
                    errors.append("workflow_graph.archive_status must be a non-empty string when provided")
                else:
                    statuses.add(archive_status)

            for status in sorted(statuses):
                stage = stage_metadata.get(status)
                if not isinstance(stage, dict):
                    errors.append(f"stage_metadata must define object for status '{status}'")
                    continue
                skill_ref = stage.get("stage_skill_ref")
                if not isinstance(skill_ref, str) or not skill_ref.strip():
                    errors.append(f"stage_metadata['{status}'].stage_skill_ref is required")

        if isinstance(initial_status, str) and initial_status and not errors:
            reachable = {initial_status}
            stack = [initial_status]
            while stack:
                node = stack.pop()
                for nxt in adjacency.get(node, set()):
                    if nxt not in reachable:
                        reachable.add(nxt)
                        stack.append(nxt)
            unreachable = sorted(workflow_statuses - reachable)
            if unreachable:
                errors.append(f"unreachable statuses in workflow graph: {', '.join(unreachable)}")

        return errors

    def _serialize_definition(self, definition: FormTypeDefinition) -> dict[str, Any]:
        workflow_graph = self._decode_json(definition.workflow_graph)
        if isinstance(workflow_graph, dict):
            workflow_graph = self._normalize_stage_graph_decisions(workflow_graph)
        return {
            "id": definition.id,
            "type_key": definition.type_key,
            "version": definition.version,
            "lifecycle_state": definition.lifecycle_state.value,
            "description": definition.description,
            "workflow_graph": workflow_graph,
            "stage_metadata": self._decode_json(definition.stage_metadata),
            "validation_errors": self._decode_json(definition.validation_errors),
            "created_at": definition.created_at.isoformat() if definition.created_at else None,
            "updated_at": definition.updated_at.isoformat() if definition.updated_at else None,
        }

    def _serialize_form(self, form: FormLedger) -> dict[str, Any]:
        return {
            "form_id": form.form_id,
            "form_type_key": form.form_type_key,
            "form_type_version": form.form_type_version,
            "current_status": form.current_status,
            "current_holder_node": form.current_holder_node,
            "sender_node_id": form.sender_node_id,
            "target_node_id": form.target_node_id,
            "subject": form.subject,
            "history_log": self._decode_json(form.history_log),
        }

    def _workspace_root(self) -> Path:
        return Path(__file__).resolve().parents[3] / "workspace"

    def _workspace_forms_root(self) -> Path:
        return self._workspace_root() / "forms"

    def _workspace_form_skills_root(self, *, type_key: str) -> Path:
        return self._workspace_forms_root() / type_key / "skills"

    def _load_workspace_workflow_payload(self, *, workflow_path: Path) -> dict[str, Any]:
        try:
            raw = json.loads(workflow_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in {workflow_path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"workflow file must contain a JSON object: {workflow_path}")
        return raw

    def _form_definition_changed(
        self,
        *,
        existing: FormTypeDefinition | None,
        description: str | None,
        workflow_graph: dict[str, Any],
        stage_metadata: dict[str, Any],
    ) -> bool:
        if existing is None:
            return True

        existing_graph = self._decode_json(existing.workflow_graph)
        existing_stages = self._decode_json(existing.stage_metadata)
        if isinstance(existing_graph, dict) and self._is_stage_graph(existing_graph):
            existing_graph = self._normalize_stage_graph_decisions(existing_graph)

        return not (
            existing.description == description
            and existing_graph == workflow_graph
            and existing_stages == stage_metadata
        )

    def _persist_workflow_copy(
        self,
        *,
        type_key: str,
        version: str,
        description: str | None,
        workflow_graph: dict[str, Any],
        stage_metadata: dict[str, Any],
    ) -> None:
        if not self._is_stage_graph(workflow_graph):
            return

        forms_root = self._workspace_forms_root() / type_key
        forms_root.mkdir(parents=True, exist_ok=True)

        payload: dict[str, Any]
        if isinstance(workflow_graph, dict):
            payload = self._normalize_stage_graph_decisions(workflow_graph)
        else:
            payload = {}
        payload["form_type"] = type_key
        payload["version"] = version
        if description:
            payload["description"] = description
        if "stage_metadata" not in payload:
            payload["stage_metadata"] = stage_metadata

        workflow_path = forms_root / "workflow.json"
        workflow_path.write_text(
            json.dumps(payload, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )

    def _validate_type_key(self, type_key: str) -> None:
        if not self._TYPE_KEY_PATTERN.fullmatch(type_key):
            raise HTTPException(
                status_code=400,
                detail=(
                    "form type key must be snake_case "
                    "(regex: ^[a-z][a-z0-9_]*$)"
                ),
            )

    def _parse_lifecycle(self, raw: str) -> FormTypeLifecycle:
        try:
            return FormTypeLifecycle(raw.upper())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"invalid lifecycle_state '{raw}'") from exc

    def _require(self, value: str | None, field: str) -> str:
        if value is None or not value.strip():
            raise HTTPException(status_code=400, detail=f"{field} is required")
        return value.strip()

    def _optional_str(self, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = value.strip()
        if not parsed:
            return None
        return parsed

    def _resolve_actor_node_id_from_request(self, *, request: FormsActionRequest) -> str:
        actor_node_id = self._optional_str(request.actor_node_id)
        actor_node_name = self._optional_str(request.actor_node_name)

        resolved_from_name: str | None = None
        if actor_node_name:
            resolved_from_name = self._resolve_unique_node_id_by_name(actor_node_name)

        if actor_node_id and resolved_from_name and actor_node_id != resolved_from_name:
            raise HTTPException(
                status_code=400,
                detail=(
                    "actor_node_id and actor_node_name resolve to different nodes: "
                    f"actor_node_id='{actor_node_id}' actor_node_name='{actor_node_name}'"
                ),
            )

        if actor_node_id:
            self._require_node(actor_node_id)
            return actor_node_id
        if resolved_from_name:
            return resolved_from_name

        raise HTTPException(status_code=400, detail="actor_node_id or actor_node_name is required")

    def _resolve_message_form_definition(self) -> FormTypeDefinition:
        try:
            return self._repository.ensure_builtin_message_form_type()
        except ValueError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    def _message_initial_status(self, workflow_graph: dict[str, Any]) -> str:
        initial_status = workflow_graph.get("initial_status")
        if not isinstance(initial_status, str) or not initial_status.strip():
            raise HTTPException(status_code=500, detail="message form type has invalid workflow_graph.initial_status")
        return initial_status.strip()

    def _message_dispatch_decision(self, workflow_graph: dict[str, Any]) -> str:
        decision = workflow_graph.get("dispatch_decision")
        if isinstance(decision, str) and decision.strip():
            return decision.strip()
        return "dispatch_to_target"

    def _message_acknowledge_decision(self, workflow_graph: dict[str, Any]) -> str:
        decision = workflow_graph.get("acknowledge_decision")
        if isinstance(decision, str) and decision.strip():
            return decision.strip()
        return "acknowledge_read"

    def _message_archive_status(self, workflow_graph: dict[str, Any]) -> str:
        archive_status = workflow_graph.get("archive_status")
        if isinstance(archive_status, str) and archive_status.strip():
            return archive_status.strip()
        end_status = workflow_graph.get("end_status")
        if isinstance(end_status, str) and end_status.strip():
            return end_status.strip()
        return FormStatus.ARCHIVED.value

    def _has_transition_edge(
        self,
        *,
        workflow_graph: dict[str, Any],
        from_status: str,
        decision_key: str,
    ) -> bool:
        raw_edges = workflow_graph.get("edges")
        if not isinstance(raw_edges, list):
            return False
        for edge in raw_edges:
            if not isinstance(edge, dict):
                continue
            if edge.get("from") != from_status:
                continue
            if str(edge.get("decision") or "") != decision_key:
                continue
            return True
        return False

    def _require_node(self, node_id: str) -> None:
        node = self._repository.get_node(node_id=node_id)
        if node is None:
            raise HTTPException(status_code=400, detail=f"node '{node_id}' not found")

    def _resolve_unique_node_id_by_name(self, node_name: str) -> str:
        nodes = self._repository.list_nodes_by_name(node_name=node_name)
        if not nodes:
            raise HTTPException(status_code=400, detail=f"node name '{node_name}' not found")
        if len(nodes) > 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"node name '{node_name}' is not unique ({len(nodes)} matches); "
                    "use static_node with explicit node id"
                ),
            )
        return nodes[0].id

    def _decode_json(self, raw: str | None) -> Any:
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
