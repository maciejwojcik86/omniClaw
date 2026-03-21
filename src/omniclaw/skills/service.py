from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any

from fastapi import HTTPException

from omniclaw.company_paths import CompanyPaths, build_company_paths
from omniclaw.config import Settings, load_effective_company_settings, load_settings
from omniclaw.db.enums import MasterSkillLifecycleStatus, NodeSkillAssignmentSource, NodeType
from omniclaw.db.models import MasterSkill, Node
from omniclaw.db.repository import KernelRepository
from omniclaw.skills.schemas import SkillsActionRequest


_DEFAULT_ACCESS_SCOPE = "descendant"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


class SkillsService:
    MANAGER_POLICY_SKILL_NAMES = ("manage-agent-instructions", "manage-team-budgets")

    def __init__(
        self,
        *,
        repository: KernelRepository,
        settings: Settings | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings or load_settings()
        self._company_paths: CompanyPaths = build_company_paths(self._settings)
        self._repo_root = _repo_root()
        self._company_master_skills_root = self._company_paths.master_skills_root

    def execute(self, request: SkillsActionRequest) -> dict[str, object]:
        self.sync_company_master_skill_catalog()

        if request.action == "list_master_skills":
            return {
                "action": request.action,
                "items": [self._serialize_master_skill(item) for item in self._repository.list_master_skills()],
            }

        if request.action == "list_active_master_skills":
            return {
                "action": request.action,
                "items": [
                    self._serialize_master_skill(item)
                    for item in self._repository.list_master_skills(
                        lifecycle_status=MasterSkillLifecycleStatus.ACTIVE,
                        loose_only=True,
                    )
                ],
            }

        if request.action == "draft_master_skill":
            skill_name = self._require_skill_name(request.skill_name)
            copied_skill = self._copy_loose_skill_from_source(
                skill_name=skill_name,
                source_path=request.source_path,
                existing_required=False,
                lifecycle_status=MasterSkillLifecycleStatus.DRAFT,
                description=request.description,
                version=request.version,
            )
            return {
                "action": request.action,
                "skill": self._serialize_master_skill(copied_skill),
            }

        if request.action == "update_master_skill":
            skill_name = self._require_skill_name(request.skill_name)
            copied_skill = self._copy_loose_skill_from_source(
                skill_name=skill_name,
                source_path=request.source_path,
                existing_required=True,
                lifecycle_status=None,
                description=request.description,
                version=request.version,
            )
            return {
                "action": request.action,
                "skill": self._serialize_master_skill(copied_skill),
            }

        if request.action == "set_master_skill_status":
            skill_name = self._require_skill_name(request.skill_name)
            lifecycle_status = request.lifecycle_status
            if lifecycle_status is None:
                raise HTTPException(status_code=422, detail="lifecycle_status is required")
            skill = self._repository.get_master_skill(name=skill_name)
            if skill is None:
                raise HTTPException(status_code=404, detail=f"master skill '{skill_name}' not found")
            if skill.form_type_key is not None:
                raise HTTPException(status_code=400, detail="form-linked skills cannot change lifecycle through this action")
            updated = self._repository.set_master_skill_lifecycle_status(
                name=skill_name,
                lifecycle_status=lifecycle_status,
            )
            return {
                "action": request.action,
                "skill": self._serialize_master_skill(updated),
            }

        if request.action == "sync_agent_skills" and request.sync_scope == "all_active_agents":
            return self.sync_all_active_agents()

        target = self._resolve_target_agent_node(request=request)

        if request.action == "sync_agent_skills":
            actor = self._resolve_actor_node(request=request, required=False)
            if actor is not None:
                self._authorize_target(actor=actor, target=target)
            return {
                "action": request.action,
                "scope": "target",
                "target": self._serialize_target(target),
                "sync": self.sync_node_skills(node=target),
            }

        if request.action == "list_agent_skill_assignments":
            actor = self._resolve_actor_node(request=request, required=False)
            if actor is not None:
                self._authorize_target(actor=actor, target=target)
            return {
                "action": request.action,
                "target": self._serialize_target(target),
                "assignments": self._serialize_assignment_summary(node=target),
            }

        actor = self._resolve_actor_node(request=request, required=False)
        if actor is not None:
            self._authorize_target(actor=actor, target=target)

        if request.action == "assign_master_skills":
            skill_names = self._normalize_skill_names(request.skill_names)
            if not skill_names:
                raise HTTPException(status_code=422, detail="skill_names must contain at least one skill")
            assigned = self.assign_loose_skills_to_node(
                node=target,
                skill_names=skill_names,
                assigned_by_node=actor,
            )
            sync_result = self.sync_node_skills(node=target)
            return {
                "action": request.action,
                "target": self._serialize_target(target),
                "assigned": [self._serialize_master_skill(item) for item in assigned],
                "assignments": self._serialize_assignment_summary(node=target),
                "sync": sync_result,
            }

        if request.action == "remove_master_skills":
            skill_names = self._normalize_skill_names(request.skill_names)
            if not skill_names:
                raise HTTPException(status_code=422, detail="skill_names must contain at least one skill")
            removed = self.remove_loose_skills_from_node(node=target, skill_names=skill_names)
            sync_result = self.sync_node_skills(node=target)
            return {
                "action": request.action,
                "target": self._serialize_target(target),
                "removed_skill_names": removed,
                "assignments": self._serialize_assignment_summary(node=target),
                "sync": sync_result,
            }

        raise HTTPException(status_code=400, detail=f"Unsupported skills action '{request.action}'")

    def sync_company_master_skill_catalog(self) -> list[MasterSkill]:
        synced: list[MasterSkill] = []
        if not self._company_master_skills_root.exists():
            return synced

        for source_dir in sorted(self._company_master_skills_root.iterdir()):
            if not source_dir.is_dir():
                continue
            skill_file = source_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            defaults = self._load_skill_manifest_defaults(source_dir=source_dir, skill_name=source_dir.name)
            existing = self._repository.get_master_skill(name=defaults["name"])
            lifecycle_status = (
                existing.lifecycle_status if existing is not None else MasterSkillLifecycleStatus.ACTIVE
            )
            synced.append(
                self._repository.upsert_master_skill(
                    name=defaults["name"],
                    form_type_key=None,
                    master_path=str(source_dir.resolve()),
                    description=defaults["description"],
                    version=defaults["version"],
                    lifecycle_status=lifecycle_status,
                )
            )
        return synced

    def sync_manager_policy_assignments(self) -> dict[str, object]:
        self.sync_company_master_skill_catalog()
        manager_skills = self._repository.list_master_skills(
            names=list(self.MANAGER_POLICY_SKILL_NAMES),
            loose_only=True,
        )
        manager_skill_ids = {item.id: item.name for item in manager_skills}
        manager_skill_id_list = list(manager_skill_ids.keys())
        installed = 0
        removed = 0
        items: list[dict[str, object]] = []

        for node in self._repository.list_nodes_with_workspaces():
            has_subordinates = bool(self._repository.list_children(parent_node_id=node.id))
            existing_default_rows = {
                row.skill_id: row
                for row in self._repository.list_node_skill_assignments(
                    node_id=node.id,
                    assignment_source=NodeSkillAssignmentSource.DEFAULT,
                )
                if row.skill_id in manager_skill_id_list
            }
            desired_ids = set(manager_skill_id_list if has_subordinates else [])
            for skill_id in desired_ids:
                if skill_id in existing_default_rows:
                    continue
                self._repository.upsert_node_skill_assignment(
                    node_id=node.id,
                    skill_id=skill_id,
                    assignment_source=NodeSkillAssignmentSource.DEFAULT,
                )
                installed += 1
                items.append(
                    {
                        "node": node.name,
                        "skill_name": manager_skill_ids[skill_id],
                        "status": "assigned",
                    }
                )
            stale_ids = [skill_id for skill_id in existing_default_rows if skill_id not in desired_ids]
            if stale_ids:
                removed += self._repository.delete_node_skill_assignments(
                    node_id=node.id,
                    skill_ids=stale_ids,
                    assignment_source=NodeSkillAssignmentSource.DEFAULT,
                )
                for skill_id in stale_ids:
                    items.append(
                        {
                            "node": node.name,
                            "skill_name": manager_skill_ids[skill_id],
                            "status": "removed",
                        }
                    )

        return {
            "status": "ok",
            "managed_skill_names": list(self.MANAGER_POLICY_SKILL_NAMES),
            "assigned": installed,
            "removed": removed,
            "items": items,
        }

    def seed_default_loose_skills_for_node(self, *, node: Node) -> list[MasterSkill]:
        self.sync_company_master_skill_catalog()
        default_names = self._default_agent_skill_names()
        if not default_names:
            self._repository.replace_node_skill_assignments_for_source(
                node_id=node.id,
                assignment_source=NodeSkillAssignmentSource.DEFAULT,
                skill_ids=[],
            )
            return []

        skills = self._repository.list_master_skills(
            names=default_names,
            lifecycle_status=MasterSkillLifecycleStatus.ACTIVE,
            loose_only=True,
        )
        skills_by_name = {skill.name: skill for skill in skills}
        missing = [name for name in default_names if name not in skills_by_name]
        if missing:
            raise ValueError(
                "configured default loose skills are missing or inactive: "
                + ", ".join(sorted(missing))
            )
        self._repository.replace_node_skill_assignments_for_source(
            node_id=node.id,
            assignment_source=NodeSkillAssignmentSource.DEFAULT,
            skill_ids=[skills_by_name[name].id for name in default_names],
        )
        return [skills_by_name[name] for name in default_names]

    def assign_loose_skills_to_node(
        self,
        *,
        node: Node,
        skill_names: list[str],
        assigned_by_node: Node | None,
    ) -> list[MasterSkill]:
        normalized_names = self._normalize_skill_names(skill_names)
        skills = self._repository.list_master_skills(
            names=normalized_names,
            lifecycle_status=MasterSkillLifecycleStatus.ACTIVE,
            loose_only=True,
        )
        skills_by_name = {skill.name: skill for skill in skills}
        missing = [name for name in normalized_names if name not in skills_by_name]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=(
                    "manual assignment only accepts active loose master skills; missing or invalid: "
                    + ", ".join(sorted(missing))
                ),
            )
        for skill in skills_by_name.values():
            self._repository.upsert_node_skill_assignment(
                node_id=node.id,
                skill_id=skill.id,
                assignment_source=NodeSkillAssignmentSource.MANUAL,
                assigned_by_node_id=assigned_by_node.id if assigned_by_node is not None else None,
            )
        return [skills_by_name[name] for name in normalized_names]

    def remove_loose_skills_from_node(self, *, node: Node, skill_names: list[str]) -> list[str]:
        normalized_names = self._normalize_skill_names(skill_names)
        skills = self._repository.list_master_skills(names=normalized_names, loose_only=True)
        skills_by_name = {skill.name: skill for skill in skills}
        removable_skill_ids = [skills_by_name[name].id for name in normalized_names if name in skills_by_name]
        if removable_skill_ids:
            self._repository.delete_node_skill_assignments(
                node_id=node.id,
                skill_ids=removable_skill_ids,
                assignment_source=NodeSkillAssignmentSource.MANUAL,
            )
        return [name for name in normalized_names if name in skills_by_name]

    def sync_all_active_agents(self) -> dict[str, object]:
        manager_policy_sync = self.sync_manager_policy_assignments()
        items: list[dict[str, object]] = []
        synced = 0
        failed = 0
        for node in self._repository.list_active_agent_nodes_with_workspaces():
            item = self.sync_node_skills(node=node)
            items.append(item)
            if item["status"] == "synced":
                synced += 1
            else:
                failed += 1
        payload = {
            "action": "sync_agent_skills",
            "scope": "all_active_agents",
            "summary": {
                "scanned": len(items),
                "synced": synced,
                "failed": failed,
            },
            "manager_policy_assignments": manager_policy_sync,
            "items": items,
        }
        payload["skill_distribution"] = payload["manager_policy_assignments"]
        return payload

    def sync_node_skills(self, *, node: Node) -> dict[str, object]:
        workspace = self._resolve_workspace_root(node)
        if workspace is None:
            return {
                "node": node.name,
                "status": "failed",
                "error": "node has no valid workspace_root",
            }

        skills_root = workspace / "skills"
        existing_entries = sorted(item.name for item in skills_root.iterdir()) if skills_root.exists() else []
        staging_root = workspace / ".skills-sync-staging"
        if staging_root.exists():
            if staging_root.is_dir():
                shutil.rmtree(staging_root)
            else:
                staging_root.unlink()

        aggregated = self._aggregate_assignment_details(node=node)
        try:
            staging_root.mkdir(parents=True, exist_ok=True)
            for item in aggregated:
                skill = item["skill"]
                source_dir = Path(skill.master_path).expanduser().resolve()
                if not source_dir.exists() or not source_dir.is_dir():
                    raise RuntimeError(f"master skill source not found for '{skill.name}': {source_dir}")
                target_dir = staging_root / skill.name
                shutil.copytree(source_dir, target_dir)
                manifest_error = self._ensure_skill_manifest(
                    target_skill_dir=target_dir,
                    skill_name=skill.name,
                    manifest_defaults=self._load_skill_manifest_defaults(source_dir=source_dir, skill_name=skill.name),
                )
                if manifest_error is not None:
                    raise RuntimeError(f"failed writing skill manifest for '{skill.name}': {manifest_error}")
            if skills_root.exists():
                if skills_root.is_dir():
                    shutil.rmtree(skills_root)
                else:
                    skills_root.unlink()
            staging_root.rename(skills_root)
        except OSError as exc:
            if staging_root.exists():
                if staging_root.is_dir():
                    shutil.rmtree(staging_root)
                else:
                    staging_root.unlink()
            return {
                "node": node.name,
                "status": "failed",
                "path": str(skills_root.resolve()),
                "error": str(exc),
            }
        except RuntimeError as exc:
            if staging_root.exists():
                if staging_root.is_dir():
                    shutil.rmtree(staging_root)
                else:
                    staging_root.unlink()
            return {
                "node": node.name,
                "status": "failed",
                "path": str(skills_root.resolve()),
                "error": str(exc),
            }

        installed_names = [item["skill"].name for item in aggregated]
        removed_names = [name for name in existing_entries if name not in installed_names]
        return {
            "node": node.name,
            "status": "synced",
            "path": str(skills_root.resolve()),
            "installed": installed_names,
            "removed": removed_names,
            "assignment_count": len(aggregated),
        }

    def _copy_loose_skill_from_source(
        self,
        *,
        skill_name: str,
        source_path: str | None,
        existing_required: bool,
        lifecycle_status: MasterSkillLifecycleStatus | None,
        description: str | None,
        version: str | None,
    ) -> MasterSkill:
        source_dir = self._require_source_path(source_path)
        existing = self._repository.get_master_skill(name=skill_name)
        if existing_required and existing is None:
            raise HTTPException(status_code=404, detail=f"master skill '{skill_name}' not found")
        if not existing_required and existing is not None:
            raise HTTPException(status_code=409, detail=f"master skill '{skill_name}' already exists")
        if existing is not None and existing.form_type_key is not None:
            raise HTTPException(status_code=400, detail="form-linked skills cannot be updated through loose-skill actions")

        target_dir = self._company_master_skills_root / skill_name
        self._replace_directory_tree(source=source_dir, target=target_dir)
        defaults = self._load_skill_manifest_defaults(source_dir=target_dir, skill_name=skill_name)
        target_lifecycle = lifecycle_status or (existing.lifecycle_status if existing is not None else MasterSkillLifecycleStatus.ACTIVE)
        return self._repository.upsert_master_skill(
            name=defaults["name"],
            form_type_key=None,
            master_path=str(target_dir.resolve()),
            description=description.strip() if isinstance(description, str) and description.strip() else defaults["description"],
            version=version.strip() if isinstance(version, str) and version.strip() else defaults["version"],
            lifecycle_status=target_lifecycle,
        )

    def _aggregate_assignment_details(self, *, node: Node) -> list[dict[str, object]]:
        by_skill_id: dict[str, dict[str, object]] = {}
        for assignment, skill in self._repository.list_node_skill_assignment_details(node_id=node.id):
            bucket = by_skill_id.setdefault(
                skill.id,
                {
                    "skill": skill,
                    "sources": set(),
                },
            )
            sources = bucket["sources"]
            if isinstance(sources, set):
                sources.add(assignment.assignment_source.value)
        items = list(by_skill_id.values())
        items.sort(key=lambda item: item["skill"].name)
        return items

    def _serialize_assignment_summary(self, *, node: Node) -> list[dict[str, object]]:
        payload: list[dict[str, object]] = []
        for item in self._aggregate_assignment_details(node=node):
            skill = item["skill"]
            sources = sorted(item["sources"]) if isinstance(item["sources"], set) else []
            payload.append(
                {
                    **self._serialize_master_skill(skill),
                    "assignment_sources": sources,
                }
            )
        return payload

    def _resolve_actor_node(
        self,
        *,
        request: SkillsActionRequest,
        required: bool,
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

    def _resolve_target_agent_node(self, *, request: SkillsActionRequest) -> Node:
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
        payload = load_effective_company_settings(self._settings)
        instructions = payload.get("instructions")
        if not isinstance(instructions, dict):
            return _DEFAULT_ACCESS_SCOPE
        raw_scope = instructions.get("access_scope")
        if not isinstance(raw_scope, str):
            return _DEFAULT_ACCESS_SCOPE
        normalized = raw_scope.strip()
        if normalized in {"direct_children", "descendant"}:
            return normalized
        return _DEFAULT_ACCESS_SCOPE

    def _default_agent_skill_names(self) -> list[str]:
        payload = load_effective_company_settings(self._settings)
        skills = payload.get("skills")
        if not isinstance(skills, dict):
            return []
        raw_names = skills.get("default_agent_skill_names")
        if not isinstance(raw_names, list):
            return []
        return self._normalize_skill_names([item for item in raw_names if isinstance(item, str)])

    def _require_skill_name(self, raw_skill_name: str | None) -> str:
        if isinstance(raw_skill_name, str) and raw_skill_name.strip():
            return raw_skill_name.strip()
        raise HTTPException(status_code=422, detail="skill_name is required")

    def _normalize_skill_names(self, raw_names: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in raw_names:
            raw = item.strip()
            if not raw or raw in seen:
                continue
            normalized.append(raw)
            seen.add(raw)
        return normalized

    def _require_source_path(self, source_path: str | None) -> Path:
        if not isinstance(source_path, str) or not source_path.strip():
            raise HTTPException(status_code=422, detail="source_path is required")
        source_dir = Path(source_path).expanduser().resolve()
        if not source_dir.exists() or not source_dir.is_dir():
            raise HTTPException(status_code=404, detail=f"source_path '{source_dir}' not found")
        if not (source_dir / "SKILL.md").exists():
            raise HTTPException(status_code=400, detail=f"source_path '{source_dir}' must contain SKILL.md")
        return source_dir

    def _replace_directory_tree(self, *, source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source == target:
            return
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)

    def _load_skill_manifest_defaults(self, *, source_dir: Path, skill_name: str) -> dict[str, str]:
        defaults = {
            "name": skill_name,
            "version": "1.0.0",
            "description": f"Master skill package '{skill_name}'.",
            "author": "omniclaw-kernel",
        }
        manifest_path = source_dir / "skill.json"
        if manifest_path.exists():
            try:
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {}
            if isinstance(payload, dict):
                for key in ("name", "version", "description", "author"):
                    raw = payload.get(key)
                    if isinstance(raw, str) and raw.strip():
                        defaults[key] = raw.strip()
        frontmatter = self._parse_markdown_frontmatter(source_dir / "SKILL.md")
        for key in ("name", "version", "description", "author"):
            raw = frontmatter.get(key)
            if isinstance(raw, str) and raw.strip():
                defaults[key] = raw.strip()
        return defaults

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
            "description": manifest_defaults.get("description", f"Master skill package '{skill_name}'."),
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

    def _resolve_workspace_root(self, node: Node) -> Path | None:
        if not node.workspace_root:
            return None
        return Path(node.workspace_root).expanduser().resolve()

    def _serialize_master_skill(self, skill: MasterSkill) -> dict[str, object]:
        return {
            "id": skill.id,
            "name": skill.name,
            "form_type_key": skill.form_type_key,
            "master_path": skill.master_path,
            "description": skill.description,
            "version": skill.version,
            "validation_status": skill.validation_status.value,
            "lifecycle_status": skill.lifecycle_status.value,
            "manual_assignable": skill.form_type_key is None and skill.lifecycle_status == MasterSkillLifecycleStatus.ACTIVE,
        }

    def _serialize_target(self, node: Node) -> dict[str, object]:
        return {
            "id": node.id,
            "name": node.name,
            "role_name": node.role_name,
            "workspace_root": node.workspace_root,
        }
