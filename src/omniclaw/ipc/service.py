from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import fcntl
import json
import re
import shutil
import time
from typing import Any, TextIO

from fastapi import HTTPException

from omniclaw.company_paths import CompanyPaths, build_company_paths, repo_workspace_root
from omniclaw.config import Settings
from omniclaw.db.models import FormLedger, FormTypeDefinition, Node
from omniclaw.db.repository import KernelRepository
from omniclaw.forms.schemas import FormsActionRequest
from omniclaw.instructions.service import InstructionsService
from omniclaw.forms.service import FormsService
from omniclaw.ipc.schemas import IpcActionRequest
from omniclaw.skills.service import SkillsService


class IpcRouterService:
    _UUID_PATTERN = re.compile(
        r"^[0-9a-fA-F]{8}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{12}$"
    )

    def __init__(
        self,
        *,
        settings: Settings,
        repository: KernelRepository,
        instructions_service: InstructionsService | None = None,
        skills_service: SkillsService | None = None,
    ) -> None:
        self._settings = settings
        self._company_paths: CompanyPaths = build_company_paths(self._settings)
        self._repository = repository
        self._skills_service = skills_service or SkillsService(repository=repository, settings=settings)
        self._forms_service = FormsService(
            repository=repository,
            settings=settings,
            skills_service=self._skills_service,
        )
        self._instructions_service = instructions_service or InstructionsService(
            settings=settings,
            repository=repository,
            skills_service=self._skills_service,
        )

    def execute(self, request: IpcActionRequest) -> dict[str, object]:
        if request.action not in {"scan_messages", "scan_forms"}:
            raise HTTPException(status_code=400, detail=f"Unsupported IPC action '{request.action}'")
        return self._scan_forms(limit=request.limit, action=request.action)

    def _scan_forms(self, *, limit: int, action: str) -> dict[str, object]:
        started = time.monotonic()
        instructions_sync = self._sync_instructions_prepass()
        items: list[dict[str, object]] = []
        scanned = 0
        routed = 0
        undelivered = 0
        skipped = 0

        for sender in self._repository.list_nodes_with_workspaces():
            if scanned >= limit:
                break
            sender_workspace = self._resolve_workspace_root(sender)
            if sender_workspace is None:
                continue

            for queue_rel in self._settings.ipc_queue_paths:
                if scanned >= limit:
                    break
                queue_path = self._resolve_within_workspace(sender_workspace, queue_rel)
                if queue_path is None or not queue_path.exists() or not queue_path.is_dir():
                    continue

                for source_path in sorted(queue_path.iterdir()):
                    if scanned >= limit:
                        break
                    if not source_path.is_file():
                        continue
                    if source_path.suffix.lower() not in {".md", ".markdown"}:
                        skipped += 1
                        continue

                    try:
                        claimed_handle = self._try_claim_source_file(source_path)
                    except OSError as exc:
                        scanned += 1
                        item = self._undelivered(
                            sender=sender,
                            source_path=str(source_path.resolve()),
                            failure_reason=f"unable to claim queued form file: {exc}",
                            form_type=None,
                            form_id=None,
                            target=None,
                            stage=None,
                            decision=None,
                            next_stage=None,
                        )
                        items.append(item)
                        undelivered += 1
                        continue
                    if claimed_handle is None:
                        skipped += 1
                        continue

                    with claimed_handle:
                        scanned += 1
                        item = self._process_source_file(
                            sender=sender,
                            sender_workspace=sender_workspace,
                            source_path=source_path,
                        )
                    items.append(item)
                    if item["status"] == "routed":
                        routed += 1
                    elif item["status"] == "undelivered":
                        undelivered += 1

        finished = time.monotonic()
        return {
            "action": action,
            "summary": {
                "scanned": scanned,
                "routed": routed,
                "undelivered": undelivered,
                "skipped": skipped,
                "instructions_rendered": int(instructions_sync.get("summary", {}).get("rendered", 0)),
                "instructions_failed": int(instructions_sync.get("summary", {}).get("failed", 0)),
                "duration_ms": int((finished - started) * 1000),
                "scan_interval_seconds": self._settings.ipc_router_scan_interval_seconds,
            },
            "instructions_sync": instructions_sync,
            "items": items,
        }

    def _sync_instructions_prepass(self) -> dict[str, object]:
        try:
            return self._instructions_service.sync_all_active_agents()
        except Exception as exc:
            return {
                "action": "sync_render",
                "scope": "all_active_agents",
                "summary": {
                    "scanned": 0,
                    "rendered": 0,
                    "failed": 1,
                },
                "skill_distribution": {
                    "skill_name": InstructionsService.MANAGER_SKILL_NAME,
                    "status": "failed",
                    "installed": 0,
                    "removed": 0,
                    "items": [],
                },
                "items": [],
                "error": str(exc),
            }

    def _try_claim_source_file(self, source_path: Path) -> TextIO | None:
        try:
            handle = source_path.open("r", encoding="utf-8")
        except FileNotFoundError:
            return None

        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            return None
        except OSError:
            handle.close()
            raise
        return handle

    def _process_source_file(
        self,
        *,
        sender: Node,
        sender_workspace: Path,
        source_path: Path,
    ) -> dict[str, object]:
        original_source_path = str(source_path.resolve())

        try:
            raw_content = source_path.read_text(encoding="utf-8")
        except OSError as exc:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason=f"unable to read form file: {exc}",
                form_type=None,
                form_id=None,
                target=None,
                stage=None,
                decision=None,
                next_stage=None,
            )

        frontmatter, body, parse_error = self._parse_frontmatter(raw_content)
        if parse_error is not None:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason=parse_error,
                form_type=None,
                form_id=None,
                target=None,
                stage=None,
                decision=None,
                next_stage=None,
            )

        form_type = self._resolve_form_type(frontmatter)
        frontmatter_decision = self._frontmatter_decision(frontmatter=frontmatter)
        if not form_type:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason="frontmatter form_type is required (or legacy type: MESSAGE)",
                form_type=None,
                form_id=self._optional_str(frontmatter.get("form_id")),
                target=self._optional_str(frontmatter.get("target")),
                stage=self._optional_str(frontmatter.get("stage")),
                decision=frontmatter_decision,
                next_stage=None,
            )

        definition = self._resolve_active_form_definition(form_type)
        if definition is None:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason=f"active form type '{form_type}' not found",
                form_type=form_type,
                form_id=self._optional_str(frontmatter.get("form_id")),
                target=self._optional_str(frontmatter.get("target")),
                stage=self._optional_str(frontmatter.get("stage")),
                decision=frontmatter_decision,
                next_stage=None,
            )

        workflow_graph = self._decode_json(definition.workflow_graph)
        stage_graph, graph_error = self._load_stage_graph(workflow_graph)
        if graph_error is not None:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason=graph_error,
                form_type=form_type,
                form_id=self._optional_str(frontmatter.get("form_id")),
                target=self._optional_str(frontmatter.get("target")),
                stage=self._optional_str(frontmatter.get("stage")),
                decision=frontmatter_decision,
                next_stage=None,
            )

        current_stage = self._resolve_current_stage(frontmatter=frontmatter, stage_graph=stage_graph)
        if current_stage not in stage_graph["stages"]:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason=f"stage '{current_stage}' is not defined for form type '{form_type}'",
                form_type=form_type,
                form_id=self._optional_str(frontmatter.get("form_id")),
                target=self._optional_str(frontmatter.get("target")),
                stage=current_stage,
                decision=frontmatter_decision,
                next_stage=None,
            )

        decision_key = self._resolve_decision_key(frontmatter=frontmatter)
        if not decision_key:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason="frontmatter decision is required for queued forms",
                form_type=form_type,
                form_id=self._optional_str(frontmatter.get("form_id")),
                target=self._optional_str(frontmatter.get("target")),
                stage=current_stage,
                decision=frontmatter_decision,
                next_stage=None,
            )

        stage_payload = stage_graph["stages"][current_stage]
        decisions = self._stage_decisions(stage_payload)
        if not isinstance(decisions, dict):
            decisions = {}

        raw_next_stage = decisions.get(decision_key)
        next_stage = raw_next_stage.strip() if isinstance(raw_next_stage, str) else ""
        if not next_stage:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason=(
                    f"no decision '{decision_key}' defined from stage '{current_stage}' "
                    f"for form type '{form_type}'"
                ),
                form_type=form_type,
                form_id=self._optional_str(frontmatter.get("form_id")),
                target=self._optional_str(frontmatter.get("target")),
                stage=current_stage,
                decision=decision_key,
                next_stage=None,
            )
        if next_stage not in stage_graph["stages"]:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason=f"next stage '{next_stage}' is not defined for form type '{form_type}'",
                form_type=form_type,
                form_id=self._optional_str(frontmatter.get("form_id")),
                target=self._optional_str(frontmatter.get("target")),
                stage=current_stage,
                decision=decision_key,
                next_stage=next_stage,
            )

        next_stage_payload = stage_graph["stages"][next_stage]
        next_stage_terminal = self._is_terminal_stage(next_stage_payload)
        next_stage_target_is_none = self._stage_target_is_none(next_stage_payload)
        requires_stage_skill = (not next_stage_terminal) or (not next_stage_target_is_none)

        required_skill = self._required_skill_name(next_stage_payload)
        if requires_stage_skill and required_skill is None:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason=(
                    f"stage '{next_stage}' requires required_skill "
                    "(non-terminal stage or terminal stage with holder target)"
                ),
                form_type=form_type,
                form_id=self._optional_str(frontmatter.get("form_id")),
                target=self._optional_str(frontmatter.get("target")),
                stage=current_stage,
                decision=decision_key,
                next_stage=next_stage,
            )

        master_skill_dir: Path | None = None
        if required_skill is not None:
            master_skill_dir, skill_error = self._resolve_master_skill_dir(
                form_type=form_type,
                skill_name=required_skill,
            )
            if skill_error is not None:
                return self._undelivered(
                    sender=sender,
                    source_path=original_source_path,
                    failure_reason=skill_error,
                    form_type=form_type,
                    form_id=self._optional_str(frontmatter.get("form_id")),
                    target=self._optional_str(frontmatter.get("target")),
                    stage=current_stage,
                    decision=decision_key,
                    next_stage=next_stage,
                )

        existing_form, existing_error = self._resolve_existing_form(frontmatter=frontmatter)
        if existing_error is not None:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason=existing_error,
                form_type=form_type,
                form_id=self._optional_str(frontmatter.get("form_id")),
                target=self._optional_str(frontmatter.get("target")),
                stage=current_stage,
                decision=decision_key,
                next_stage=next_stage,
            )

        if existing_form is not None:
            if existing_form.current_status != current_stage:
                return self._undelivered(
                    sender=sender,
                    source_path=original_source_path,
                    failure_reason=(
                        f"stale form stage: file stage '{current_stage}' does not match "
                        f"ledger stage '{existing_form.current_status}'"
                    ),
                    form_type=form_type,
                    form_id=existing_form.form_id,
                    target=self._optional_str(frontmatter.get("target")),
                    stage=current_stage,
                    decision=decision_key,
                    next_stage=next_stage,
                )
            if existing_form.current_holder_node and existing_form.current_holder_node != sender.id:
                return self._undelivered(
                    sender=sender,
                    source_path=original_source_path,
                    failure_reason=(
                        "form holder mismatch: current holder is "
                        f"'{existing_form.current_holder_node}', actor is '{sender.id}'"
                    ),
                    form_type=form_type,
                    form_id=existing_form.form_id,
                    target=self._optional_str(frontmatter.get("target")),
                    stage=current_stage,
                    decision=decision_key,
                    next_stage=next_stage,
                )

        if existing_form is None and current_stage != stage_graph["start_stage"]:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason=(
                    f"new forms must begin at start stage '{stage_graph['start_stage']}', got '{current_stage}'"
                ),
                form_type=form_type,
                form_id=self._optional_str(frontmatter.get("form_id")),
                target=self._optional_str(frontmatter.get("target")),
                stage=current_stage,
                decision=decision_key,
                next_stage=next_stage,
            )

        if existing_form is None:
            initiator_allowed, initiator_allowlist_error = self._is_allowed_initiator(
                sender=sender,
                stage_graph=stage_graph,
            )
            if not initiator_allowed:
                return self._undelivered(
                    sender=sender,
                    source_path=original_source_path,
                    failure_reason=initiator_allowlist_error or "sender is not permitted to initiate this form type",
                    form_type=form_type,
                    form_id=self._optional_str(frontmatter.get("form_id")),
                    target=self._optional_str(frontmatter.get("target")),
                    stage=current_stage,
                    decision=decision_key,
                    next_stage=next_stage,
                )

        initiator_node_id, initiator_error = self._resolve_initiator_node_id(
            sender=sender,
            frontmatter=frontmatter,
            existing_form=existing_form,
        )
        if initiator_error is not None:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason=initiator_error,
                form_type=form_type,
                form_id=self._optional_str(frontmatter.get("form_id")),
                target=self._optional_str(frontmatter.get("target")),
                stage=current_stage,
                decision=decision_key,
                next_stage=next_stage,
            )

        target_node, target_mode, target_context, target_error = self._resolve_target_node(
            target_spec=next_stage_payload.get("target"),
            frontmatter=frontmatter,
            initiator_node_id=initiator_node_id,
        )
        if target_error is not None:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason=target_error,
                form_type=form_type,
                form_id=self._optional_str(frontmatter.get("form_id")),
                target=self._optional_str(frontmatter.get("target")),
                stage=current_stage,
                decision=decision_key,
                next_stage=next_stage,
            )

        context: dict[str, Any] = {"initiator_node_id": initiator_node_id}
        context.update(target_context)
        if target_node is not None:
            context.setdefault("target_node_id", target_node.id)

        distribution_nodes = self._resolve_skill_distribution_nodes(
            target_mode=target_mode,
            holder_node=target_node,
        )
        if required_skill is not None and master_skill_dir is not None:
            distribution_error = self._distribute_stage_skill(
                master_skill_dir=master_skill_dir,
                skill_name=required_skill,
                target_nodes=distribution_nodes,
            )
            if distribution_error is not None:
                return self._undelivered(
                    sender=sender,
                    source_path=original_source_path,
                    failure_reason=distribution_error,
                    form_type=form_type,
                    form_id=self._optional_str(frontmatter.get("form_id")),
                    target=target_node.name if target_node else self._optional_str(frontmatter.get("target")),
                    stage=current_stage,
                    decision=decision_key,
                    next_stage=next_stage,
                )

        form_id: str
        if existing_form is not None:
            form_id = existing_form.form_id
        else:
            try:
                created = self._forms_service.execute(
                    FormsActionRequest(
                        action="create_form",
                        type_key=form_type,
                        version=definition.version,
                        form_id_hint=self._build_form_id(source_path.name),
                        initial_status=current_stage,
                        initial_holder_node_id=sender.id,
                        actor_node_id=sender.id,
                    )
                )
            except HTTPException as exc:
                return self._undelivered(
                    sender=sender,
                    source_path=original_source_path,
                    failure_reason=f"unable to create form instance: {exc.detail}",
                    form_type=form_type,
                    form_id=None,
                    target=target_node.name if target_node else self._optional_str(frontmatter.get("target")),
                    stage=current_stage,
                    decision=decision_key,
                    next_stage=next_stage,
                )
            form_payload = created.get("form") if isinstance(created, dict) else None
            if not isinstance(form_payload, dict) or not isinstance(form_payload.get("form_id"), str):
                return self._undelivered(
                    sender=sender,
                    source_path=original_source_path,
                    failure_reason="create_form returned invalid payload",
                    form_type=form_type,
                    form_id=None,
                    target=target_node.name if target_node else self._optional_str(frontmatter.get("target")),
                    stage=current_stage,
                    decision=decision_key,
                    next_stage=next_stage,
                )
            form_id = str(form_payload["form_id"])

        routed_frontmatter = dict(frontmatter)
        # Runtime-only routing details stay in DB events, not in routed frontmatter.
        for transient_key in (
            "in_reply_to",
            "initiator_node_id",
            "target_node_id",
            "agent",
            "stage_skill",
            "target_agent",
            "previous_decision",
            "previous_transition",
            "transition",
        ):
            routed_frontmatter.pop(transient_key, None)
        routed_frontmatter.update(
            {
                "form_type": form_type,
                "form_id": form_id,
                "stage": next_stage,
                "agent": target_node.name if target_node is not None else "",
                "stage_skill": required_skill or "",
                "decision": "",
                "sender": sender.name,
                # `target` remains an authoring-time routing input for queued forms.
                "target": "",
            }
        )
        routed_frontmatter["target_agent"] = self._build_target_agent_hint(
            stage_graph=stage_graph,
            stage_name=next_stage,
            frontmatter=routed_frontmatter,
            initiator_node_id=initiator_node_id,
        )
        routed_content = self._render_frontmatter(
            frontmatter=routed_frontmatter,
            body=body,
        )

        sender_archive_dir = self._resolve_within_workspace(sender_workspace, self._settings.ipc_archive_rel)
        if sender_archive_dir is None:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason="invalid sender archive path configuration",
                form_type=form_type,
                form_id=form_id,
                target=target_node.name if target_node else None,
                stage=current_stage,
                decision=decision_key,
                next_stage=next_stage,
            )

        sender_archive_dir.mkdir(parents=True, exist_ok=True)
        sender_archive_path = self._resolve_unique_path(sender_archive_dir / source_path.name)

        delivery_path: Path | None = None
        if target_node is not None:
            target_workspace = self._resolve_workspace_root(target_node)
            if target_workspace is None:
                return self._undelivered(
                    sender=sender,
                    source_path=original_source_path,
                    failure_reason=f"target node '{target_node.name}' has no valid workspace_root",
                    form_type=form_type,
                    form_id=form_id,
                    target=target_node.name,
                    stage=current_stage,
                    decision=decision_key,
                    next_stage=next_stage,
                )
            inbox_dir = self._resolve_within_workspace(target_workspace, self._settings.ipc_inbox_new_rel)
            if inbox_dir is None:
                return self._undelivered(
                    sender=sender,
                    source_path=original_source_path,
                    failure_reason="invalid target inbox path configuration",
                    form_type=form_type,
                    form_id=form_id,
                    target=target_node.name,
                    stage=current_stage,
                    decision=decision_key,
                    next_stage=next_stage,
                )
            inbox_dir.mkdir(parents=True, exist_ok=True)
            delivery_path = self._resolve_unique_path(inbox_dir / source_path.name)

        backup_path = self._resolve_archive_copy_path(
            form_type=form_type,
            form_id=form_id,
            stage=next_stage,
            filename=source_path.name,
        )

        try:
            if delivery_path is not None:
                delivery_path.write_text(routed_content, encoding="utf-8")
                self._ensure_group_writable(delivery_path)
            sender_archive_path.write_text(routed_content, encoding="utf-8")
            self._ensure_group_writable(sender_archive_path)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_text(routed_content, encoding="utf-8")
            self._ensure_group_writable(backup_path)
            source_path.unlink()
        except OSError as exc:
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason=f"filesystem routing failure: {exc}",
                form_type=form_type,
                form_id=form_id,
                target=target_node.name if target_node else None,
                stage=current_stage,
                decision=decision_key,
                next_stage=next_stage,
            )

        try:
            transitioned = self._forms_service.execute(
                FormsActionRequest(
                    action="transition_form",
                    form_id=form_id,
                    decision_key=decision_key,
                    actor_node_id=sender.id,
                    context=context,
                    payload={
                        "source_path": original_source_path,
                        "delivery_path": str(delivery_path.resolve()) if delivery_path is not None else None,
                        "archive_path": str(sender_archive_path.resolve()),
                        "backup_path": str(backup_path.resolve()),
                        "stage": next_stage,
                        "required_skill": required_skill,
                    },
                    set_fields={
                        "source_path": original_source_path,
                        "delivery_path": str(delivery_path.resolve()) if delivery_path is not None else None,
                        "archive_path": str(sender_archive_path.resolve()),
                        "message_name": source_path.name,
                        "subject": self._optional_str(frontmatter.get("subject")),
                        "target_node_id": target_node.id if target_node is not None else None,
                        "failure_reason": None,
                    },
                )
            )
        except HTTPException as exc:
            self._rollback_routing_files(
                source_path=source_path,
                sender_archive_path=sender_archive_path,
                delivery_path=delivery_path,
                backup_path=backup_path,
            )
            return self._undelivered(
                sender=sender,
                source_path=original_source_path,
                failure_reason=f"transition_form failed after filesystem route: {exc.detail}",
                form_type=form_type,
                form_id=form_id,
                target=target_node.name if target_node else None,
                stage=current_stage,
                decision=decision_key,
                next_stage=next_stage,
            )

        transitioned_form = transitioned.get("form") if isinstance(transitioned, dict) else None
        final_holder_node = None
        if isinstance(transitioned_form, dict):
            raw_holder = transitioned_form.get("current_holder_node")
            if isinstance(raw_holder, str) and raw_holder:
                final_holder_node = self._repository.get_node(node_id=raw_holder)

        return {
            "status": "routed",
            "form_id": form_id,
            "form_type": form_type,
            "sender": sender.name,
            "target": final_holder_node.name if final_holder_node else (target_node.name if target_node else None),
            "stage": current_stage,
            "decision": decision_key,
            "next_stage": next_stage,
            "source_path": original_source_path,
            "delivery_path": str(delivery_path.resolve()) if delivery_path is not None else None,
            "archive_path": str(sender_archive_path.resolve()),
            "backup_path": str(backup_path.resolve()),
            "dead_letter_path": None,
            "feedback_path": None,
            "failure_reason": None,
        }

    def _resolve_form_type(self, frontmatter: dict[str, str]) -> str | None:
        raw = frontmatter.get("form_type")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()

        legacy = frontmatter.get("type")
        if not isinstance(legacy, str) or not legacy.strip():
            return None
        if legacy.strip().upper() == "MESSAGE":
            return "message"
        return legacy.strip()

    def _resolve_active_form_definition(self, form_type: str) -> FormTypeDefinition | None:
        if form_type == "message":
            try:
                return self._repository.ensure_builtin_message_form_type()
            except ValueError:
                return None
        return self._repository.get_form_type_definition(type_key=form_type, active_only=True)

    def _load_stage_graph(self, workflow_graph: Any) -> tuple[dict[str, Any], str | None]:
        if not isinstance(workflow_graph, dict):
            return {}, "workflow graph is invalid"
        raw_stages = workflow_graph.get("stages")
        if not isinstance(raw_stages, dict) or not raw_stages:
            return {}, "active form workflow must define workflow_graph.stages"

        start_stage = workflow_graph.get("start_stage")
        if not isinstance(start_stage, str) or not start_stage.strip():
            first_stage = next(iter(raw_stages.keys()))
            if not isinstance(first_stage, str) or not first_stage:
                return {}, "workflow_graph.start_stage is required"
            start_stage = first_stage
        start_stage = start_stage.strip()

        end_stage = workflow_graph.get("end_stage")
        if not isinstance(end_stage, str) or not end_stage.strip():
            for stage_name, stage_payload in raw_stages.items():
                if isinstance(stage_name, str) and isinstance(stage_payload, dict) and stage_payload.get("is_terminal") is True:
                    end_stage = stage_name
                    break
        if not isinstance(end_stage, str) or not end_stage.strip():
            return {}, "workflow_graph.end_stage is required"
        end_stage = end_stage.strip()

        return {
            "start_stage": start_stage,
            "end_stage": end_stage,
            "stages": raw_stages,
            "initiator_allowlist": workflow_graph.get("initiator_allowlist"),
        }, None

    def _resolve_current_stage(self, *, frontmatter: dict[str, str], stage_graph: dict[str, Any]) -> str:
        raw_stage = frontmatter.get("stage")
        if isinstance(raw_stage, str) and raw_stage.strip():
            return raw_stage.strip()
        return str(stage_graph["start_stage"])

    def _resolve_decision_key(
        self,
        *,
        frontmatter: dict[str, str],
    ) -> str:
        raw_decision = self._frontmatter_decision(frontmatter=frontmatter)
        if not isinstance(raw_decision, str):
            return ""
        return raw_decision.strip()

    def _frontmatter_decision(self, *, frontmatter: dict[str, str]) -> str | None:
        raw_decision = frontmatter.get("decision")
        if isinstance(raw_decision, str):
            parsed = raw_decision.strip()
            if parsed:
                return parsed

        legacy_transition = frontmatter.get("transition")
        if not isinstance(legacy_transition, str):
            return None
        parsed = legacy_transition.strip()
        if not parsed:
            return None
        return parsed

    def _stage_decisions(self, stage_payload: Any) -> Any:
        if not isinstance(stage_payload, dict):
            return None
        decisions = stage_payload.get("decisions")
        if decisions is not None:
            return decisions
        return stage_payload.get("transitions")

    def _required_skill_name(self, stage_payload: Any) -> str | None:
        if not isinstance(stage_payload, dict):
            return None
        required_skill = stage_payload.get("required_skill")
        if not isinstance(required_skill, str) or not required_skill.strip():
            return None
        return required_skill.strip()

    def _is_terminal_stage(self, stage_payload: Any) -> bool:
        return isinstance(stage_payload, dict) and stage_payload.get("is_terminal") is True

    def _stage_target_is_none(self, stage_payload: Any) -> bool:
        if not isinstance(stage_payload, dict):
            return False
        target = stage_payload.get("target")
        if target is None:
            return True
        if not isinstance(target, str):
            return False
        return target.strip().lower() in {"none", "null", "{{none}}"}

    def _resolve_master_skill_dir(self, *, form_type: str, skill_name: str) -> tuple[Path | None, str | None]:
        safe_skill_rel, safe_error = self._safe_relative_path(skill_name)
        if safe_error is not None:
            return None, f"required_skill '{skill_name}' is invalid: {safe_error}"

        skill_dir = self._workspace_form_skills_root(form_type=form_type) / safe_skill_rel
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            return None, f"required skill '{skill_name}' missing at {skill_file}"
        return skill_dir, None

    def _resolve_existing_form(self, *, frontmatter: dict[str, str]) -> tuple[FormLedger | None, str | None]:
        form_id = self._optional_str(frontmatter.get("form_id"))
        if not form_id:
            return None, None
        existing = self._repository.get_form_ledger(form_id=form_id)
        if existing is None:
            return None, f"form_id '{form_id}' not found"
        return existing, None

    def _resolve_initiator_node_id(
        self,
        *,
        sender: Node,
        frontmatter: dict[str, str],
        existing_form: FormLedger | None,
    ) -> tuple[str, str | None]:
        if existing_form is not None:
            if isinstance(existing_form.sender_node_id, str) and existing_form.sender_node_id:
                return existing_form.sender_node_id, None

        raw_initiator_node_id = self._optional_str(frontmatter.get("initiator_node_id"))
        if raw_initiator_node_id:
            node = self._repository.get_node(node_id=raw_initiator_node_id)
            if node is None:
                return "", f"initiator_node_id '{raw_initiator_node_id}' not found"
            return node.id, None

        raw_initiator = self._optional_str(frontmatter.get("initiator"))
        if raw_initiator:
            node, error = self._resolve_node_reference(raw_initiator)
            if error is not None or node is None:
                return "", f"initiator '{raw_initiator}' could not be resolved"
            return node.id, None

        return sender.id, None

    def _is_allowed_initiator(self, *, sender: Node, stage_graph: dict[str, Any]) -> tuple[bool, str | None]:
        raw_allowlist = stage_graph.get("initiator_allowlist")
        if raw_allowlist is None:
            return True, None
        if not isinstance(raw_allowlist, list) or not raw_allowlist:
            return False, "workflow initiator_allowlist must be a non-empty array when provided"

        allowed_node_ids: set[str] = set()
        for index, raw_reference in enumerate(raw_allowlist):
            if not isinstance(raw_reference, str) or not raw_reference.strip():
                return (
                    False,
                    (
                        "workflow initiator_allowlist contains invalid reference at index "
                        f"{index}: must be non-empty node name/id or '{{{{any}}}}'"
                    ),
                )
            reference = raw_reference.strip()
            if reference == "{{any}}":
                return True, None

            node, node_error = self._resolve_node_reference(reference)
            if node_error is not None or node is None:
                reason = node_error if node_error is not None else f"node '{reference}' not found"
                return False, f"workflow initiator_allowlist[{index}] invalid: {reason}"
            allowed_node_ids.add(node.id)

        if sender.id in allowed_node_ids:
            return True, None
        return (
            False,
            (
                f"sender '{sender.name}' is not allowed to initiate this form "
                "(not in workflow initiator_allowlist)"
            ),
        )

    def _resolve_target_node(
        self,
        *,
        target_spec: Any,
        frontmatter: dict[str, str],
        initiator_node_id: str,
    ) -> tuple[Node | None, str, dict[str, str], str | None]:
        if target_spec is None:
            return None, "none", {}, None

        if not isinstance(target_spec, str) or not target_spec.strip():
            return None, "none", {}, None

        target = target_spec.strip()
        if target.lower() in {"none", "null", "{{none}}"}:
            return None, "none", {}, None

        if target == "{{initiator}}":
            node = self._repository.get_node(node_id=initiator_node_id)
            if node is None:
                return None, "single", {}, "initiator_node_id points to unknown node"
            return node, "single", {"initiator_node_id": node.id}, None

        if target == "{{any}}":
            candidate = self._optional_str(frontmatter.get("target_node_id")) or self._optional_str(frontmatter.get("target"))
            if not candidate:
                return None, "any", {}, "target is required for stages targeting {{any}}"
            node, error = self._resolve_node_reference(candidate)
            if error is not None:
                return None, "any", {}, error
            if node is None:
                return None, "any", {}, f"target '{candidate}' not found"
            return node, "any", {"target_node_id": node.id}, None

        variable_match = re.fullmatch(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}", target)
        if variable_match:
            var_name = variable_match.group(1)
            if var_name == "initiator":
                node = self._repository.get_node(node_id=initiator_node_id)
                if node is None:
                    return None, "single", {}, "initiator_node_id points to unknown node"
                return node, "single", {"initiator_node_id": node.id}, None
            if var_name == "any":
                candidate = self._optional_str(frontmatter.get("target_node_id")) or self._optional_str(frontmatter.get("target"))
            else:
                candidate = self._optional_str(frontmatter.get(f"{var_name}_node_id")) or self._optional_str(frontmatter.get(var_name))
            if not candidate:
                return None, "single", {}, f"target reference '{target}' requires frontmatter field"
            node, error = self._resolve_node_reference(candidate)
            if error is not None:
                return None, "single", {}, error
            if node is None:
                return None, "single", {}, f"target reference '{candidate}' not found"
            return node, "single", {f"{var_name}_node_id": node.id}, None

        node, error = self._resolve_node_reference(target)
        if error is not None:
            return None, "single", {}, error
        if node is None:
            return None, "single", {}, f"target '{target}' not found"
        return node, "single", {}, None

    def _build_target_agent_hint(
        self,
        *,
        stage_graph: dict[str, Any],
        stage_name: str,
        frontmatter: dict[str, Any],
        initiator_node_id: str,
    ) -> str:
        stages = stage_graph.get("stages")
        if not isinstance(stages, dict):
            return ""

        stage_payload = stages.get(stage_name)
        decisions = self._stage_decisions(stage_payload)
        if not isinstance(decisions, dict) or not decisions:
            return ""

        lines: list[str] = []
        target_labels: list[str] = []
        for decision_key, raw_next_stage in decisions.items():
            if not isinstance(decision_key, str) or not decision_key.strip():
                continue
            if not isinstance(raw_next_stage, str) or not raw_next_stage.strip():
                continue

            target_label = self._describe_stage_target(
                stage_graph=stage_graph,
                stage_name=raw_next_stage.strip(),
                frontmatter=frontmatter,
                initiator_node_id=initiator_node_id,
            )
            target_labels.append(target_label)
            lines.append(f"{decision_key.strip()}: {target_label}")

        if not lines or all(label == "none" for label in target_labels):
            return ""
        return "Leave one option that matches the chosen decision and delete the others:\n" + "\n".join(lines)

    def _describe_stage_target(
        self,
        *,
        stage_graph: dict[str, Any],
        stage_name: str,
        frontmatter: dict[str, Any],
        initiator_node_id: str,
    ) -> str:
        stages = stage_graph.get("stages")
        if not isinstance(stages, dict):
            return "none"
        stage_payload = stages.get(stage_name)
        if not isinstance(stage_payload, dict):
            return "none"
        return self._describe_target_spec(
            target_spec=stage_payload.get("target"),
            frontmatter=frontmatter,
            initiator_node_id=initiator_node_id,
        )

    def _describe_target_spec(
        self,
        *,
        target_spec: Any,
        frontmatter: dict[str, Any],
        initiator_node_id: str,
    ) -> str:
        if target_spec is None:
            return "none"
        if not isinstance(target_spec, str) or not target_spec.strip():
            return "none"

        target = target_spec.strip()
        if target.lower() in {"none", "null", "{{none}}"}:
            return "none"

        if target == "{{initiator}}":
            initiator = self._repository.get_node(node_id=initiator_node_id)
            return initiator.name if initiator is not None else "{{initiator}}"

        if target == "{{any}}":
            return "{{any}}"

        variable_match = re.fullmatch(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}", target)
        if variable_match:
            var_name = variable_match.group(1)
            if var_name == "initiator":
                initiator = self._repository.get_node(node_id=initiator_node_id)
                return initiator.name if initiator is not None else "{{initiator}}"
            if var_name == "any":
                return "{{any}}"

            candidate = self._optional_str(frontmatter.get(f"{var_name}_node_id")) or self._optional_str(
                frontmatter.get(var_name)
            )
            if candidate:
                node, error = self._resolve_node_reference(candidate)
                if error is None and node is not None:
                    return node.name
                return candidate
            return target

        node, error = self._resolve_node_reference(target)
        if error is None and node is not None:
            return node.name
        return target

    def _resolve_node_reference(self, value: str) -> tuple[Node | None, str | None]:
        return self._repository.resolve_unique_node_reference(value)

    def _resolve_skill_distribution_nodes(self, *, target_mode: str, holder_node: Node | None) -> list[Node]:
        selected: dict[str, Node] = {}
        if target_mode == "any":
            for node in self._repository.list_active_agent_nodes_with_workspaces():
                selected[node.id] = node
        if holder_node is not None:
            selected[holder_node.id] = holder_node
        return list(selected.values())

    def _distribute_stage_skill(
        self,
        *,
        master_skill_dir: Path,
        skill_name: str,
        target_nodes: list[Node],
    ) -> str | None:
        _ = (master_skill_dir, skill_name)
        if not target_nodes:
            return None

        for node in target_nodes:
            sync_result = self._skills_service.sync_node_skills(node=node)
            if sync_result["status"] != "synced":
                return (
                    f"failed to reconcile approved skills for node '{node.name}': "
                    f"{sync_result.get('error', 'unknown error')}"
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

    def _load_skill_manifest_defaults(self, *, master_skill_dir: Path, skill_name: str) -> dict[str, str]:
        defaults = {
            "name": skill_name,
            "version": "1.0.0",
            "description": f"Dispatched form skill package '{skill_name}'.",
            "author": "omniclaw-kernel",
        }

        source_manifest_path = master_skill_dir / "skill.json"
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

        frontmatter = self._parse_skill_frontmatter(master_skill_dir / "SKILL.md")
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

    def _workspace_forms_root(self) -> Path:
        if self._company_paths.forms_root.exists():
            return self._company_paths.forms_root
        return repo_workspace_root() / "forms"

    def _workspace_form_skills_root(self, *, form_type: str) -> Path:
        return self._workspace_forms_root() / form_type / "skills"

    def _workspace_form_archive_root(self) -> Path:
        return self._company_paths.form_archive_root

    def _resolve_archive_copy_path(self, *, form_type: str, form_id: str, stage: str, filename: str) -> Path:
        stage_slug = re.sub(r"[^A-Za-z0-9_-]+", "_", stage).strip("_") or "stage"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive_root = self._workspace_form_archive_root() / form_type / form_id
        return self._resolve_unique_path(archive_root / f"{timestamp}-{stage_slug}-{filename}")

    def _rollback_routing_files(
        self,
        *,
        source_path: Path,
        sender_archive_path: Path,
        delivery_path: Path | None,
        backup_path: Path,
    ) -> None:
        if delivery_path is not None and delivery_path.exists():
            try:
                delivery_path.unlink()
            except OSError:
                pass
        if backup_path.exists():
            try:
                backup_path.unlink()
            except OSError:
                pass
        if sender_archive_path.exists() and not source_path.exists():
            try:
                sender_archive_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(sender_archive_path), str(source_path))
            except OSError:
                pass

    def _ensure_group_writable(self, path: Path) -> None:
        try:
            mode = path.stat().st_mode
            path.chmod(mode | 0o20)
        except OSError:
            return

    def _undelivered(
        self,
        *,
        sender: Node,
        source_path: str,
        failure_reason: str,
        form_type: str | None,
        form_id: str | None,
        target: str | None,
        stage: str | None,
        decision: str | None,
        next_stage: str | None,
    ) -> dict[str, object]:
        source = Path(source_path).expanduser().resolve()
        dead_letter_path: str | None = None
        failure_details = failure_reason

        sender_workspace = self._resolve_workspace_root(sender)
        if source.exists() and sender_workspace is not None:
            dead_letter_dir = self._resolve_within_workspace(sender_workspace, self._settings.ipc_dead_letter_rel)
            if dead_letter_dir is not None:
                try:
                    dead_letter_dir.mkdir(parents=True, exist_ok=True)
                    dead_letter_file = self._resolve_unique_path(dead_letter_dir / source.name)
                    shutil.move(str(source), str(dead_letter_file))
                    dead_letter_path = str(dead_letter_file.resolve())
                except OSError as exc:
                    failure_details = f"{failure_reason}; dead-letter move failed: {exc}"

        feedback_path = self._write_feedback_message(
            sender=sender,
            target=target,
            failure_reason=failure_reason,
            source_path=source_path,
            stage=stage,
            decision=decision,
        )

        return {
            "status": "undelivered",
            "form_id": form_id,
            "form_type": form_type,
            "sender": sender.name,
            "target": target,
            "stage": stage,
            "decision": decision,
            "next_stage": next_stage,
            "source_path": source_path,
            "delivery_path": None,
            "archive_path": None,
            "backup_path": None,
            "dead_letter_path": dead_letter_path,
            "feedback_path": feedback_path,
            "failure_reason": failure_details,
        }

    def _write_feedback_message(
        self,
        *,
        sender: Node,
        target: str | None,
        failure_reason: str,
        source_path: str,
        stage: str | None,
        decision: str | None,
    ) -> str | None:
        recipient = self._resolve_feedback_recipient(sender=sender, target=target)
        workspace = self._resolve_workspace_root(recipient)
        if workspace is None:
            return None
        inbox_dir = self._resolve_within_workspace(workspace, self._settings.ipc_inbox_new_rel)
        if inbox_dir is None:
            return None

        source_name = Path(source_path).name or "undelivered.md"
        feedback_name = f"{Path(source_name).stem}-feedback.md"
        error_code, invalid_field = self._categorize_failure(failure_reason)
        content = self._render_frontmatter(
            frontmatter={
                "type": "MESSAGE",
                "sender": "Kernel_IPC",
                "target": recipient.name,
                "subject": f"IPC validation feedback: {source_name}",
                "error_code": error_code,
                "error_message": failure_reason,
                "invalid_field": invalid_field,
                "original_source_path": source_path,
                "original_target": target or "",
                "original_stage": stage or "",
                "original_decision": decision or "",
            },
            body=(
                "The queued form could not be routed.\n"
                "Review the structured fields in frontmatter, correct the source form, "
                "and requeue if needed."
            ),
        )
        try:
            inbox_dir.mkdir(parents=True, exist_ok=True)
            feedback_path = self._resolve_unique_path(inbox_dir / feedback_name)
            feedback_path.write_text(content, encoding="utf-8")
            self._ensure_group_writable(feedback_path)
            return str(feedback_path.resolve())
        except OSError:
            return None

    def _resolve_feedback_recipient(self, *, sender: Node, target: str | None) -> Node:
        candidate = self._optional_str(target)
        if not candidate:
            return sender
        node, error = self._resolve_node_reference(candidate)
        if error is not None or node is None:
            return sender
        if self._resolve_workspace_root(node) is None:
            return sender
        return node

    def _categorize_failure(self, failure_reason: str) -> tuple[str, str]:
        lowered = failure_reason.lower()
        if "target" in lowered:
            return "TARGET_UNRESOLVED", "target"
        if "decision" in lowered:
            return "DECISION_INVALID", "decision"
        if "stage" in lowered:
            return "STAGE_INVALID", "stage"
        if "frontmatter" in lowered:
            return "FRONTMATTER_INVALID", "frontmatter"
        return "IPC_UNDELIVERED", "unknown"

    def _parse_frontmatter(self, content: str) -> tuple[dict[str, str], str, str | None]:
        if not content.startswith("---\n"):
            return {}, content, "missing YAML frontmatter opening delimiter"

        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}, content, "invalid YAML frontmatter opening delimiter"

        closing_index: int | None = None
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                closing_index = index
                break
        if closing_index is None:
            return {}, content, "missing YAML frontmatter closing delimiter"

        frontmatter: dict[str, str] = {}
        current_block_key: str | None = None
        current_block_lines: list[str] = []

        def flush_block() -> None:
            nonlocal current_block_key, current_block_lines
            if current_block_key is None:
                return
            frontmatter[current_block_key] = "\n".join(current_block_lines).rstrip("\n")
            current_block_key = None
            current_block_lines = []

        for line in lines[1:closing_index]:
            if current_block_key is not None:
                if line.startswith("  "):
                    current_block_lines.append(line[2:])
                    continue
                if line == "":
                    current_block_lines.append("")
                    continue
                flush_block()

            stripped = line.strip()
            if not stripped:
                continue
            if ":" not in stripped:
                return {}, content, f"invalid frontmatter line: '{line}'"
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if not key:
                return {}, content, "frontmatter key must not be empty"
            if value in {"|", "|-", "|+"}:
                current_block_key = key
                current_block_lines = []
                continue
            frontmatter[key] = value

        flush_block()

        body = "\n".join(lines[closing_index + 1 :])
        return frontmatter, body, None

    def _render_frontmatter(self, *, frontmatter: dict[str, Any], body: str) -> str:
        lines = ["---"]
        for key, value in frontmatter.items():
            if key is None:
                continue
            normalized_key = str(key).strip()
            if not normalized_key:
                continue
            if value is None:
                normalized_value = ""
            else:
                normalized_value = str(value).strip("\n")
            if "\n" in normalized_value:
                lines.append(f"{normalized_key}: |")
                for value_line in normalized_value.split("\n"):
                    lines.append(f"  {value_line}")
                continue
            lines.append(f"{normalized_key}: {normalized_value.strip()}")
        lines.append("---")
        if body:
            return "\n".join(lines) + "\n\n" + body.rstrip("\n") + "\n"
        return "\n".join(lines) + "\n"

    def _resolve_workspace_root(self, node: Node) -> Path | None:
        if not node.workspace_root:
            return None
        workspace = Path(node.workspace_root).expanduser().resolve()
        if not workspace.exists():
            return None
        return workspace

    def _resolve_within_workspace(self, workspace_root: Path, relative_path: str) -> Path | None:
        normalized = relative_path.strip().strip("/")
        if not normalized:
            return None
        candidate = (workspace_root / normalized).resolve()
        try:
            candidate.relative_to(workspace_root)
        except ValueError:
            return None
        return candidate

    def _build_form_id(self, source_name: str) -> str:
        cleaned = source_name.strip()
        if cleaned.endswith(".md"):
            cleaned = cleaned[: -len(".md")]
        if cleaned.endswith(".markdown"):
            cleaned = cleaned[: -len(".markdown")]
        cleaned = cleaned.replace(" ", "-")
        cleaned = "".join(ch for ch in cleaned if ch.isalnum() or ch in {"-", "_"})
        cleaned = cleaned.strip("-")
        if not cleaned:
            return "form"
        return cleaned[:64]

    def _resolve_unique_path(self, path: Path) -> Path:
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        counter = 1
        while True:
            candidate = path.with_name(f"{stem}-{counter}{suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    def _safe_relative_path(self, raw: str) -> tuple[Path, str | None]:
        value = raw.strip()
        if not value:
            return Path("."), "path is empty"
        rel = Path(value)
        if rel.is_absolute():
            return Path("."), "absolute paths are not allowed"
        for part in rel.parts:
            if part in {"", ".", ".."}:
                return Path("."), "path traversal components are not allowed"
        return rel, None

    def _decode_json(self, raw: str | None) -> Any:
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def _optional_str(self, raw: Any) -> str | None:
        if raw is None:
            return None
        text = str(raw).strip()
        if not text:
            return None
        return text
