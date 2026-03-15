from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
from typing import Any

from fastapi import HTTPException

from omniclaw.budgets.engine import BudgetEngine
from omniclaw.config import Settings, load_settings
from omniclaw.db.enums import NodeType
from omniclaw.db.models import Node
from omniclaw.db.repository import KernelRepository
from omniclaw.instructions.schemas import InstructionsActionRequest


_PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}")
_SUPPORTED_PLACEHOLDERS = frozenset(
    {
        "node.name",
        "node.role_name",
        "node.primary_model",
        "current_time_utc",
        "manager.name",
        "manager.id",
        "line_manager",
        "subordinates_list",
        "inbox_unread_summary",
        "budget.mode",
        "budget.daily_inflow_usd",
        "budget.rollover_reserve_usd",
        "budget.remaining_usd",
        "budget.review_required_notice",
        "budget.direct_team_summary",
    }
)
_MARKDOWN_SUFFIXES = {".md", ".markdown"}
_DEFAULT_ACCESS_SCOPE = "descendant"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def derive_instruction_template_root(*, node_name: str, workspace_root: str | None) -> Path:
    if workspace_root:
        resolved_workspace = Path(workspace_root).expanduser().resolve()
        if (
            resolved_workspace.name == "workspace"
            and len(resolved_workspace.parents) >= 3
            and resolved_workspace.parent.parent.name == "agents"
        ):
            return resolved_workspace.parents[2] / "nanobots_instructions" / node_name
    return _repo_root() / "workspace" / "nanobots_instructions" / node_name


class InstructionsService:
    MANAGER_SKILL_NAME = "manage-agent-instructions"
    MANAGER_SKILL_NAMES = ("manage-agent-instructions", "manage-team-budgets")

    def __init__(
        self,
        *,
        repository: KernelRepository,
        settings: Settings | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings or load_settings()
        self._budget_engine = BudgetEngine(repository=repository, settings=self._settings)
        self._repo_root = _repo_root()
        self._default_template_path = self._repo_root / "workspace" / "nanobot_workspace_templates" / "AGENTS.md"
        if self._settings.company_config_path:
            self._company_config_path = Path(self._settings.company_config_path).expanduser().resolve()
        else:
            self._company_config_path = self._repo_root / "workspace" / "company_config.json"
        self._master_skill_dir = self._repo_root / "workspace" / "master_skills" / self.MANAGER_SKILL_NAME

    def execute(self, request: InstructionsActionRequest) -> dict[str, object]:
        if request.action == "list_accessible_targets":
            actor = self._resolve_actor_node(request=request)
            targets = [self._serialize_target(node) for node in self._list_accessible_targets(actor)]
            return {
                "action": request.action,
                "actor": self._serialize_actor(actor),
                "access_scope": self._access_scope(),
                "targets": targets,
            }

        if request.action == "sync_render" and request.sync_scope == "all_active_agents":
            return self.sync_all_active_agents()

        target = self._resolve_target_agent_node(request=request)

        if request.action == "sync_render":
            actor = self._resolve_actor_node(request=request, required=False)
            if actor is not None:
                self._authorize_target(actor=actor, target=target)
            return self._single_sync_response(target=target)

        actor = self._resolve_actor_node(request=request)
        self._authorize_target(actor=actor, target=target)

        if request.action == "get_template":
            target = self._ensure_node_instruction_state(target)
            template_path = self._template_path(target)
            return {
                "action": request.action,
                "actor": self._serialize_actor(actor),
                "target": self._serialize_target(target),
                "template": {
                    "path": str(template_path),
                    "content": template_path.read_text(encoding="utf-8"),
                },
            }

        if request.action == "preview_render":
            content = request.template_content
            if content is None:
                target = self._ensure_node_instruction_state(target)
                content = self._template_path(target).read_text(encoding="utf-8")
            rendered = self._render_template_for_node(target=target, template_content=content)
            return {
                "action": request.action,
                "actor": self._serialize_actor(actor),
                "target": self._serialize_target(target),
                "preview": rendered,
            }

        if request.action == "set_template":
            if request.template_content is None:
                raise HTTPException(status_code=422, detail="template_content is required")
            target = self._ensure_node_instruction_state(target)
            preview = self._render_template_for_node(target=target, template_content=request.template_content)
            template_path = self._template_path(target)
            template_path.parent.mkdir(parents=True, exist_ok=True)
            template_path.write_text(request.template_content.rstrip() + "\n", encoding="utf-8")
            sync_result = self._sync_node(target)
            if sync_result["status"] != "rendered":
                raise HTTPException(
                    status_code=500,
                    detail=f"template saved but render failed: {sync_result['error']}",
                )
            return {
                "action": request.action,
                "actor": self._serialize_actor(actor),
                "target": self._serialize_target(target),
                "template": {
                    "path": str(template_path),
                    "content": template_path.read_text(encoding="utf-8"),
                },
                "preview": preview,
                "render": sync_result,
            }

        raise HTTPException(status_code=400, detail=f"Unsupported instructions action '{request.action}'")

    def ensure_default_template_for_node(self, *, node: Node) -> Node:
        return self._ensure_node_instruction_state(node)

    def sync_node_render(self, *, node: Node) -> dict[str, object]:
        target = self._ensure_node_instruction_state(node)
        return self._sync_node(target)

    def sync_all_active_agents(self) -> dict[str, object]:
        skill_distribution = self.sync_manager_skill_distribution()
        items: list[dict[str, object]] = []
        rendered = 0
        failed = 0

        for node in self._repository.list_active_agent_nodes_with_workspaces():
            item = self._sync_node(node)
            items.append(item)
            if item["status"] == "rendered":
                rendered += 1
            else:
                failed += 1

        return {
            "action": "sync_render",
            "scope": "all_active_agents",
            "summary": {
                "scanned": len(items),
                "rendered": rendered,
                "failed": failed,
            },
            "skill_distribution": skill_distribution,
            "items": items,
        }

    def sync_manager_skill_distribution(self) -> dict[str, object]:
        installed = 0
        removed = 0
        items: list[dict[str, object]] = []
        skills: list[dict[str, object]] = []
        missing_sources: list[str] = []
        descriptions = {
            "manage-agent-instructions": "Kernel-backed manager workflow for reading and updating subordinate AGENTS templates.",
            "manage-team-budgets": "Kernel-backed manager workflow for reviewing and updating direct-report budgets.",
        }

        for skill_name in self.MANAGER_SKILL_NAMES:
            source_dir = self._repo_root / "workspace" / "master_skills" / skill_name
            if not source_dir.exists():
                missing_sources.append(skill_name)
                skills.append({"skill_name": skill_name, "status": "missing_source"})
                continue

            self._repository.upsert_master_skill(
                name=skill_name,
                form_type_key=None,
                master_path=str(source_dir.resolve()),
                description=descriptions.get(skill_name),
                version="1.0.0",
            )

            skill_installed = 0
            skill_removed = 0
            for node in self._repository.list_nodes_with_workspaces():
                workspace_root = self._resolve_workspace_root(node)
                if workspace_root is None:
                    continue
                target_dir = workspace_root / "skills" / skill_name
                has_subordinates = bool(self._repository.list_children(parent_node_id=node.id))
                if has_subordinates:
                    self._copy_skill_tree(source=source_dir, target=target_dir)
                    installed += 1
                    skill_installed += 1
                    items.append(
                        {
                            "node": node.name,
                            "skill_name": skill_name,
                            "status": "installed",
                            "path": str(target_dir.resolve()),
                        }
                    )
                elif target_dir.exists():
                    if target_dir.is_dir():
                        shutil.rmtree(target_dir)
                    else:
                        target_dir.unlink()
                    removed += 1
                    skill_removed += 1
                    items.append(
                        {
                            "node": node.name,
                            "skill_name": skill_name,
                            "status": "removed",
                            "path": str(target_dir.resolve()),
                        }
                    )
            skills.append(
                {
                    "skill_name": skill_name,
                    "status": "ok",
                    "installed": skill_installed,
                    "removed": skill_removed,
                }
            )

        return {
            "skill_name": self.MANAGER_SKILL_NAME,
            "status": "missing_source" if missing_sources else "ok",
            "installed": installed,
            "removed": removed,
            "missing_sources": missing_sources,
            "skills": skills,
            "items": items,
        }

    def _single_sync_response(self, *, target: Node) -> dict[str, object]:
        target = self._ensure_node_instruction_state(target)
        return {
            "action": "sync_render",
            "scope": "target",
            "target": self._serialize_target(target),
            "render": self._sync_node(target),
        }

    def _resolve_actor_node(
        self,
        *,
        request: InstructionsActionRequest,
        required: bool = True,
    ) -> Node | None:
        actor_node_id = request.actor_node_id
        actor_node_name = request.actor_node_name
        if not actor_node_id and not actor_node_name:
            if required:
                raise HTTPException(status_code=422, detail="actor_node_id or actor_node_name is required")
            return None
        actor = self._repository.get_node(node_id=actor_node_id, node_name=actor_node_name)
        if actor is None:
            raise HTTPException(status_code=404, detail="actor node not found")
        return actor

    def _resolve_target_agent_node(self, *, request: InstructionsActionRequest) -> Node:
        target_node_id = request.target_node_id
        target_node_name = request.target_node_name
        if not target_node_id and not target_node_name:
            raise HTTPException(status_code=422, detail="target_node_id or target_node_name is required")
        target = self._repository.get_node(
            node_id=target_node_id,
            node_name=target_node_name,
            node_type=NodeType.AGENT,
        )
        if target is None:
            raise HTTPException(status_code=404, detail="target AGENT node not found")
        return target

    def _authorize_target(self, *, actor: Node, target: Node) -> None:
        accessible_ids = {node.id for node in self._list_accessible_targets(actor)}
        if target.id not in accessible_ids:
            raise HTTPException(
                status_code=403,
                detail=f"actor '{actor.name}' is not allowed to manage '{target.name}'",
            )

    def _list_accessible_targets(self, actor: Node) -> list[Node]:
        access_scope = self._access_scope()
        if access_scope == "direct_children":
            return [
                node
                for node in self._repository.list_child_nodes(parent_node_id=actor.id)
                if node.type == NodeType.AGENT and node.workspace_root
            ]

        results: dict[str, Node] = {}
        pending = list(self._repository.list_child_nodes(parent_node_id=actor.id))
        while pending:
            node = pending.pop(0)
            pending.extend(self._repository.list_child_nodes(parent_node_id=node.id))
            if node.type == NodeType.AGENT and node.workspace_root:
                results.setdefault(node.id, node)
        return sorted(results.values(), key=lambda item: (item.created_at, item.name))

    def _access_scope(self) -> str:
        default_scope = _DEFAULT_ACCESS_SCOPE
        try:
            payload = json.loads(self._company_config_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return default_scope
        if not isinstance(payload, dict):
            return default_scope
        instructions = payload.get("instructions")
        if not isinstance(instructions, dict):
            return default_scope
        raw_scope = instructions.get("access_scope")
        if not isinstance(raw_scope, str):
            return default_scope
        normalized = raw_scope.strip()
        if normalized in {"direct_children", "descendant"}:
            return normalized
        return default_scope

    def _ensure_node_instruction_state(self, node: Node) -> Node:
        updates: dict[str, str] = {}
        if not node.role_name:
            inferred_role = self._infer_role_name(node)
            if inferred_role:
                updates["role_name"] = inferred_role
        if not node.instruction_template_root:
            updates["instruction_template_root"] = str(
                derive_instruction_template_root(node_name=node.name, workspace_root=node.workspace_root).resolve()
            )

        if updates:
            node = self._repository.update_node_instruction_fields(
                node_id=node.id,
                role_name=updates.get("role_name"),
                instruction_template_root=updates.get("instruction_template_root"),
            )

        template_path = self._template_path(node)
        template_path.parent.mkdir(parents=True, exist_ok=True)
        if not template_path.exists():
            template_path.write_text(self._default_template_text().rstrip() + "\n", encoding="utf-8")
        return node

    def _infer_role_name(self, node: Node) -> str | None:
        workspace_root = self._resolve_workspace_root(node)
        if workspace_root is not None:
            rendered_path = workspace_root / "AGENTS.md"
            if rendered_path.exists():
                try:
                    for line in rendered_path.read_text(encoding="utf-8").splitlines():
                        stripped = line.strip()
                        if stripped.lower().startswith("- role:"):
                            value = stripped.split(":", 1)[1].strip()
                            if value:
                                return value
                except OSError:
                    pass
        return None

    def _render_template_for_node(self, *, target: Node, template_content: str) -> dict[str, object]:
        placeholders = sorted({match.group(1).strip() for match in _PLACEHOLDER_PATTERN.finditer(template_content)})
        unknown = sorted(set(placeholders) - _SUPPORTED_PLACEHOLDERS)
        if unknown:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "template contains unsupported placeholders",
                    "unsupported_placeholders": unknown,
                },
            )

        manager = self._repository.get_manager_node(child_node_id=target.id)
        budget_context = self._budget_engine.build_budget_placeholders(node=target)
        context = {
            "node.name": target.name,
            "node.role_name": target.role_name or target.name,
            "node.primary_model": target.primary_model or "unassigned",
            "current_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "manager.name": manager.name if manager is not None else "Unassigned Manager",
            "manager.id": manager.id if manager is not None else "",
            "line_manager": manager.name if manager is not None else "Unassigned Manager",
            "subordinates_list": self._format_subordinates(target),
            "inbox_unread_summary": self._format_unread_inbox_summary(target),
            **budget_context,
        }
        rendered_content = _PLACEHOLDER_PATTERN.sub(
            lambda match: str(context[match.group(1).strip()]),
            template_content,
        )

        return {
            "target": self._serialize_target(target),
            "placeholders": placeholders,
            "rendered_content": rendered_content.rstrip() + "\n",
        }

    def _sync_node(self, node: Node) -> dict[str, object]:
        try:
            target = self._ensure_node_instruction_state(node)
            template_path = self._template_path(target)
            template_content = template_path.read_text(encoding="utf-8")
            preview = self._render_template_for_node(target=target, template_content=template_content)
            workspace_root = self._resolve_workspace_root(target)
            if workspace_root is None:
                return {
                    "node": target.name,
                    "status": "failed",
                    "error": "target node has no valid workspace_root",
                }
            rendered_path = workspace_root / "AGENTS.md"
            self._atomic_write_read_only(rendered_path, preview["rendered_content"])
            return {
                "node": target.name,
                "status": "rendered",
                "template_path": str(template_path.resolve()),
                "rendered_path": str(rendered_path.resolve()),
                "placeholders": preview["placeholders"],
            }
        except HTTPException as exc:
            return {
                "node": node.name,
                "status": "failed",
                "error": exc.detail,
            }
        except OSError as exc:
            return {
                "node": node.name,
                "status": "failed",
                "error": str(exc),
            }

    def _atomic_write_read_only(self, target_path: Path, content: str) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(target_path)
        target_path.chmod(0o444)

    def _format_subordinates(self, node: Node) -> str:
        children = [
            child
            for child in self._repository.list_child_nodes(parent_node_id=node.id)
            if child.type == NodeType.AGENT
        ]
        if not children:
            return "No direct subordinates."
        lines = [f"- {child.name}" for child in sorted(children, key=lambda item: item.name)]
        return "\n".join(lines)

    def _format_unread_inbox_summary(self, node: Node) -> str:
        workspace_root = self._resolve_workspace_root(node)
        if workspace_root is None:
            return "No unread forms."

        inbox_root = workspace_root / "inbox" / "new"
        if not inbox_root.exists() or not inbox_root.is_dir():
            return "No unread forms."

        entries: list[Path] = []
        for path in inbox_root.iterdir():
            if path.is_file() and path.suffix.lower() in _MARKDOWN_SUFFIXES:
                entries.append(path)
        if not entries:
            return "No unread forms."

        lines: list[str] = []
        for path in sorted(entries, key=lambda item: (-item.stat().st_mtime, item.name)):
            frontmatter = self._parse_markdown_frontmatter(path)
            sender = self._normalize_summary_value(frontmatter.get("sender"), default="unknown-sender")
            form_type = frontmatter.get("form_type") or frontmatter.get("type") or "unknown"
            normalized_type = str(form_type).strip()
            if normalized_type.upper() == "MESSAGE":
                normalized_type = "message"
            stage = self._normalize_summary_value(frontmatter.get("stage"), default="n/a")
            subject = self._normalize_summary_value(
                frontmatter.get("subject") or frontmatter.get("name"),
                default=path.name,
            )
            lines.append(f"- {sender} | {normalized_type} | {stage} | {subject}")
        return "\n".join(lines)

    def _parse_markdown_frontmatter(self, path: Path) -> dict[str, str]:
        try:
            content = path.read_text(encoding="utf-8")
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
        current_key: str | None = None
        current_lines: list[str] = []

        def flush_block() -> None:
            nonlocal current_key, current_lines
            if current_key is None:
                return
            frontmatter[current_key] = "\n".join(current_lines).rstrip("\n")
            current_key = None
            current_lines = []

        for line in lines[1:closing_index]:
            if current_key is not None:
                if line.startswith("  "):
                    current_lines.append(line[2:])
                    continue
                if line == "":
                    current_lines.append("")
                    continue
                flush_block()

            stripped = line.strip()
            if not stripped or ":" not in stripped:
                continue
            key, value = stripped.split(":", 1)
            normalized_value = value.strip().strip('"').strip("'")
            if normalized_value in {"|", "|-", "|+"}:
                current_key = key.strip()
                current_lines = []
                continue
            frontmatter[key.strip()] = normalized_value

        flush_block()
        return frontmatter

    def _normalize_summary_value(self, value: Any, *, default: str) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip().replace("\n", " ")
        return default

    def _template_path(self, node: Node) -> Path:
        if not node.instruction_template_root:
            raise HTTPException(status_code=500, detail="instruction_template_root is not set for node")
        return Path(node.instruction_template_root).expanduser().resolve() / "AGENTS.md"

    def _resolve_workspace_root(self, node: Node) -> Path | None:
        if not node.workspace_root:
            return None
        return Path(node.workspace_root).expanduser().resolve()

    def _default_template_text(self) -> str:
        return self._default_template_path.read_text(encoding="utf-8")

    def _copy_skill_tree(self, *, source: Path, target: Path) -> None:
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)

    def _serialize_actor(self, node: Node) -> dict[str, object]:
        return {
            "id": node.id,
            "name": node.name,
            "type": node.type.value,
        }

    def _serialize_target(self, node: Node) -> dict[str, object]:
        return {
            "id": node.id,
            "name": node.name,
            "role_name": node.role_name,
            "workspace_root": node.workspace_root,
            "instruction_template_root": node.instruction_template_root,
        }
