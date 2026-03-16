from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
from typing import Any

from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from omniclaw.company_paths import CompanyPaths, build_company_paths, repo_workspace_root
from omniclaw.config import Settings, build_settings, load_settings
from omniclaw.db.enums import (
    BudgetMode,
    FormStatus,
    FormTypeLifecycle,
    MasterSkillLifecycleStatus,
    NodeStatus,
    NodeSkillAssignmentSource,
    NodeType,
    RelationshipType,
    SkillValidationStatus,
)
from omniclaw.db.models import (
    AgentLLMCall,
    AgentSessionExport,
    Budget,
    BudgetAllocation,
    BudgetCycle,
    FormLedger,
    FormTransitionEvent,
    FormTypeDefinition,
    Hierarchy,
    MasterSkill,
    Node,
    NodeSkillAssignment,
)


class TransitionConflictError(RuntimeError):
    pass


_UNSET = object()


class KernelRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        settings: Settings | None = None,
    ):
        self._session_factory = session_factory
        if settings is not None:
            self._settings = settings
        else:
            try:
                self._settings = load_settings()
            except (FileNotFoundError, ValueError):
                self._settings = build_settings(company_workspace_root=repo_workspace_root())
        self._company_paths: CompanyPaths = build_company_paths(self._settings)

    def create_node(
        self,
        *,
        node_type: NodeType,
        name: str,
        status: NodeStatus,
        role_name: str | None = None,
        linux_uid: int | None = None,
        linux_username: str | None = None,
        linux_password: str | None = None,
        workspace_root: str | None = None,
        runtime_config_path: str | None = None,
        instruction_template_root: str | None = None,
        primary_model: str | None = None,
        autonomy_level: int = 0,
    ) -> Node:
        with self._session_factory() as session:
            node = Node(
                type=node_type,
                name=name,
                role_name=role_name,
                status=status,
                linux_uid=linux_uid,
                linux_username=linux_username,
                linux_password=linux_password,
                workspace_root=workspace_root,
                runtime_config_path=runtime_config_path,
                instruction_template_root=instruction_template_root,
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
        role_name: str | None = None,
        linux_uid: int | None = None,
        linux_username: str | None = None,
        linux_password: str | None = None,
        workspace_root: str | None = None,
        runtime_config_path: str | None = None,
        instruction_template_root: str | None = None,
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
                existing.role_name = role_name
                existing.linux_uid = linux_uid
                existing.linux_username = linux_username
                if linux_password is not None:
                    existing.linux_password = linux_password
                existing.workspace_root = workspace_root
                existing.runtime_config_path = runtime_config_path
                existing.instruction_template_root = instruction_template_root
                existing.primary_model = primary_model
                existing.autonomy_level = autonomy_level
                session.commit()
                session.refresh(existing)
                return existing, False

            created = Node(
                type=node_type,
                name=name,
                role_name=role_name,
                status=status,
                linux_uid=linux_uid,
                linux_username=linux_username,
                linux_password=linux_password,
                workspace_root=workspace_root,
                runtime_config_path=runtime_config_path,
                instruction_template_root=instruction_template_root,
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

    def list_child_nodes(
        self,
        *,
        parent_node_id: str,
        node_type: NodeType | None = None,
    ) -> list[Node]:
        with self._session_factory() as session:
            query = (
                session.query(Node)
                .join(Hierarchy, Hierarchy.child_node_id == Node.id)
                .filter(Hierarchy.parent_node_id == parent_node_id)
            )
            if node_type is not None:
                query = query.filter(Node.type == node_type)
            return query.order_by(Node.created_at.asc()).all()

    def get_manager_node(self, *, child_node_id: str) -> Node | None:
        with self._session_factory() as session:
            return (
                session.query(Node)
                .join(Hierarchy, Hierarchy.parent_node_id == Node.id)
                .filter(Hierarchy.child_node_id == child_node_id)
                .order_by(Hierarchy.created_at.asc(), Node.created_at.asc())
                .first()
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

    def update_node_instruction_fields(
        self,
        *,
        node_id: str,
        role_name: str | None = None,
        instruction_template_root: str | None = None,
    ) -> Node:
        with self._session_factory() as session:
            node = (
                session.query(Node)
                .filter(Node.id == node_id)
                .order_by(Node.created_at.asc())
                .first()
            )
            if node is None:
                raise ValueError(f"node '{node_id}' not found")

            if role_name is not None:
                node.role_name = role_name
            if instruction_template_root is not None:
                node.instruction_template_root = instruction_template_root
            session.commit()
            session.refresh(node)
            return node

    def update_node_instruction_fields(
        self,
        *,
        node_id: str,
        role_name: str | None = None,
        instruction_template_root: str | None = None,
    ) -> Node:
        with self._session_factory() as session:
            node = (
                session.query(Node)
                .filter(Node.id == node_id)
                .order_by(Node.created_at.asc())
                .first()
            )
            if node is None:
                raise ValueError(f"node '{node_id}' not found")

            if role_name is not None:
                node.role_name = role_name
            if instruction_template_root is not None:
                node.instruction_template_root = instruction_template_root
            session.commit()
            session.refresh(node)
            return node

    # ---------------------------------------------------------------------
    # Budget tracking operations
    # ---------------------------------------------------------------------

    def upsert_budget(
        self,
        *,
        node_id: str,
        virtual_api_key: str | None = None,
        daily_limit_usd: Decimal | float | int | str | None = None,
        current_daily_allowance: Decimal | float | int | str | None = None,
        current_spend: Decimal | float | int | str | None = None,
        parent_node_id: str | None | object = _UNSET,
        allocated_percentage: Decimal | float | int | str | None = None,
        budget_mode: BudgetMode | str | None = None,
        rollover_reserve_usd: Decimal | float | int | str | None = None,
        review_required_at: datetime | None | object = _UNSET,
    ) -> Budget:
        with self._session_factory() as session:
            budget = session.query(Budget).filter(Budget.node_id == node_id).first()
            if budget is None:
                budget = Budget(
                    node_id=node_id,
                    virtual_api_key=virtual_api_key,
                )
                if daily_limit_usd is not None:
                    budget.daily_limit_usd = self._to_decimal(daily_limit_usd)
                if current_daily_allowance is not None:
                    budget.current_daily_allowance = self._to_decimal(current_daily_allowance)
                if current_spend is not None:
                    budget.current_spend = self._to_decimal(current_spend)
                if parent_node_id is not _UNSET:
                    budget.parent_node_id = parent_node_id
                if allocated_percentage is not None:
                    budget.allocated_percentage = self._to_decimal(allocated_percentage)
                if budget_mode is not None:
                    budget.budget_mode = self._coerce_budget_mode(budget_mode)
                if rollover_reserve_usd is not None:
                    budget.rollover_reserve_usd = self._to_decimal(rollover_reserve_usd)
                if review_required_at is not _UNSET:
                    budget.review_required_at = review_required_at
                session.add(budget)
            else:
                if virtual_api_key is not None:
                    budget.virtual_api_key = virtual_api_key
                if daily_limit_usd is not None:
                    budget.daily_limit_usd = self._to_decimal(daily_limit_usd)
                if current_daily_allowance is not None:
                    budget.current_daily_allowance = self._to_decimal(current_daily_allowance)
                if current_spend is not None:
                    budget.current_spend = self._to_decimal(current_spend)
                if parent_node_id is not _UNSET:
                    budget.parent_node_id = parent_node_id
                if allocated_percentage is not None:
                    budget.allocated_percentage = self._to_decimal(allocated_percentage)
                if budget_mode is not None:
                    budget.budget_mode = self._coerce_budget_mode(budget_mode)
                if rollover_reserve_usd is not None:
                    budget.rollover_reserve_usd = self._to_decimal(rollover_reserve_usd)
                if review_required_at is not _UNSET:
                    budget.review_required_at = review_required_at
            session.commit()
            session.refresh(budget)
            return budget

    def get_budget(self, *, node_id: str) -> Budget | None:
        with self._session_factory() as session:
            return session.query(Budget).filter(Budget.node_id == node_id).first()

    def list_budgets(self, *, node_ids: list[str] | None = None) -> list[Budget]:
        with self._session_factory() as session:
            query = session.query(Budget)
            if node_ids:
                query = query.filter(Budget.node_id.in_(node_ids))
            return query.order_by(Budget.created_at.asc()).all()

    def replace_budget_allocations(
        self,
        *,
        manager_node_id: str,
        allocations: list[tuple[str, float]],
    ) -> list[BudgetAllocation]:
        with self._session_factory() as session:
            session.query(BudgetAllocation).filter(
                BudgetAllocation.manager_node_id == manager_node_id
            ).delete()
            for child_node_id, percentage in allocations:
                session.add(
                    BudgetAllocation(
                        manager_node_id=manager_node_id,
                        child_node_id=child_node_id,
                        percentage=percentage,
                    )
                )
            session.commit()
            return (
                session.query(BudgetAllocation)
                .filter(BudgetAllocation.manager_node_id == manager_node_id)
                .order_by(BudgetAllocation.created_at.asc(), BudgetAllocation.child_node_id.asc())
                .all()
            )

    def list_budget_allocations(
        self,
        *,
        manager_node_id: str | None = None,
        child_node_id: str | None = None,
    ) -> list[BudgetAllocation]:
        with self._session_factory() as session:
            query = session.query(BudgetAllocation)
            if manager_node_id is not None:
                query = query.filter(BudgetAllocation.manager_node_id == manager_node_id)
            if child_node_id is not None:
                query = query.filter(BudgetAllocation.child_node_id == child_node_id)
            return query.order_by(
                BudgetAllocation.manager_node_id.asc(),
                BudgetAllocation.created_at.asc(),
                BudgetAllocation.child_node_id.asc(),
            ).all()

    def get_budget_cycle(self, *, cycle_date: date) -> BudgetCycle | None:
        with self._session_factory() as session:
            return (
                session.query(BudgetCycle)
                .filter(BudgetCycle.cycle_date == cycle_date)
                .order_by(BudgetCycle.created_at.asc())
                .first()
            )

    def upsert_budget_cycle(
        self,
        *,
        cycle_date: date,
        company_budget_usd: Decimal | float | int | str,
        root_allocator_node_id: str | None,
        executed_at: datetime | None = None,
    ) -> BudgetCycle:
        with self._session_factory() as session:
            cycle = (
                session.query(BudgetCycle)
                .filter(BudgetCycle.cycle_date == cycle_date)
                .order_by(BudgetCycle.created_at.asc())
                .first()
            )
            if cycle is None:
                cycle = BudgetCycle(
                    cycle_date=cycle_date,
                    company_budget_usd=self._to_decimal(company_budget_usd),
                    root_allocator_node_id=root_allocator_node_id,
                    executed_at=executed_at or datetime.now(timezone.utc),
                )
                session.add(cycle)
            else:
                cycle.company_budget_usd = self._to_decimal(company_budget_usd)
                cycle.root_allocator_node_id = root_allocator_node_id
                cycle.executed_at = executed_at or datetime.now(timezone.utc)
            session.commit()
            session.refresh(cycle)
            return cycle

    # ---------------------------------------------------------------------
    # Usage and Session tracking operations
    # ---------------------------------------------------------------------

    def insert_agent_llm_call(
        self,
        *,
        node_id: str,
        session_key: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        reasoning_tokens: int = 0,
        total_tokens: int = 0,
        estimated_cost_usd: Decimal | float | int | str = 0.0,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        duration_ms: int | None = None,
    ) -> AgentLLMCall:
        with self._session_factory() as session:
            call_record = AgentLLMCall(
                node_id=node_id,
                session_key=session_key,
                model=model,
                provider=provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                reasoning_tokens=reasoning_tokens,
                total_tokens=total_tokens,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
            )
            call_record.estimated_cost_usd = self._to_decimal(estimated_cost_usd)
            
            session.add(call_record)
            session.commit()
            session.refresh(call_record)
            return call_record

    @staticmethod
    def _to_decimal(value: Decimal | float | int | str) -> Decimal:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def _coerce_budget_mode(raw_mode: BudgetMode | str) -> BudgetMode:
        if isinstance(raw_mode, BudgetMode):
            return raw_mode
        return BudgetMode(str(raw_mode).strip().lower())

    @staticmethod
    def _coerce_master_skill_lifecycle_status(
        raw_status: MasterSkillLifecycleStatus | str,
    ) -> MasterSkillLifecycleStatus:
        if isinstance(raw_status, MasterSkillLifecycleStatus):
            return raw_status
        return MasterSkillLifecycleStatus(str(raw_status).strip().upper())

    @staticmethod
    def _coerce_node_skill_assignment_source(
        raw_source: NodeSkillAssignmentSource | str,
    ) -> NodeSkillAssignmentSource:
        if isinstance(raw_source, NodeSkillAssignmentSource):
            return raw_source
        return NodeSkillAssignmentSource(str(raw_source).strip().upper())

    def insert_agent_session_export(
        self,
        *,
        node_id: str,
        session_key: str,
        export_path: str,
        messages_count: int = 0,
    ) -> AgentSessionExport:
        with self._session_factory() as session:
            export_record = AgentSessionExport(
                node_id=node_id,
                session_key=session_key,
                export_path=export_path,
                messages_count=messages_count,
            )
            session.add(export_record)
            session.commit()
            session.refresh(export_record)
            return export_record

    def list_agent_llm_calls(
        self,
        *,
        node_id: str | None = None,
        session_key: str | None = None,
        limit: int | None = None,
    ) -> list[AgentLLMCall]:
        with self._session_factory() as session:
            query = session.query(AgentLLMCall)
            if node_id is not None:
                query = query.filter(AgentLLMCall.node_id == node_id)
            if session_key is not None:
                query = query.filter(AgentLLMCall.session_key == session_key)
            query = query.order_by(AgentLLMCall.start_time.asc(), AgentLLMCall.created_at.asc())
            if limit is not None:
                query = query.limit(limit)
            return query.all()

    def list_recent_session_summaries(self, *, node_id: str, limit: int = 10) -> list[dict[str, Any]]:
        with self._session_factory() as session:
            rows = (
                session.query(
                    AgentLLMCall.session_key.label("session_key"),
                    func.min(AgentLLMCall.start_time).label("started_at"),
                    func.max(AgentLLMCall.end_time).label("ended_at"),
                    func.count(AgentLLMCall.id).label("llm_call_count"),
                    func.coalesce(func.sum(AgentLLMCall.total_tokens), 0).label("total_tokens"),
                    func.coalesce(func.sum(AgentLLMCall.estimated_cost_usd), 0).label("cost_usd"),
                    func.max(AgentLLMCall.created_at).label("last_created_at"),
                )
                .filter(
                    AgentLLMCall.node_id == node_id,
                    AgentLLMCall.session_key.is_not(None),
                )
                .group_by(AgentLLMCall.session_key)
                .order_by(desc("last_created_at"), desc("started_at"))
                .limit(limit)
                .all()
            )
            return [
                {
                    "session_key": row.session_key,
                    "started_at": row.started_at,
                    "ended_at": row.ended_at,
                    "llm_call_count": int(row.llm_call_count or 0),
                    "total_tokens": int(row.total_tokens or 0),
                    "cost_usd": float(row.cost_usd or 0.0),
                }
                for row in rows
                if row.session_key is not None
            ]

    def sum_agent_llm_costs(self, *, node_id: str | None = None, session_key: str | None = None) -> Decimal:
        with self._session_factory() as session:
            query = session.query(func.coalesce(func.sum(AgentLLMCall.estimated_cost_usd), 0))
            if node_id is not None:
                query = query.filter(AgentLLMCall.node_id == node_id)
            if session_key is not None:
                query = query.filter(AgentLLMCall.session_key == session_key)
            value = query.scalar()
            return self._to_decimal(value or 0)

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
                f"'{self._company_paths.forms_root / 'message' / 'workflow.json'}'; "
                "publish and activate a message workflow"
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
        lifecycle_status: MasterSkillLifecycleStatus = MasterSkillLifecycleStatus.ACTIVE,
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
        normalized_lifecycle = self._coerce_master_skill_lifecycle_status(lifecycle_status)

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
                    lifecycle_status=normalized_lifecycle,
                )
                session.add(existing)
            else:
                existing.form_type_key = normalized_form_type_key
                existing.master_path = normalized_path
                existing.description = normalized_description
                existing.version = normalized_version
                existing.validation_status = validation_status
                existing.lifecycle_status = normalized_lifecycle
            session.commit()
            session.refresh(existing)
            return existing

    def get_master_skill(
        self,
        *,
        skill_id: str | None = None,
        name: str | None = None,
    ) -> MasterSkill | None:
        if not skill_id and not name:
            raise ValueError("skill_id or name is required")

        with self._session_factory() as session:
            query = session.query(MasterSkill)
            if skill_id is not None:
                query = query.filter(MasterSkill.id == skill_id)
            if name is not None:
                query = query.filter(MasterSkill.name == name.strip())
            return query.order_by(MasterSkill.created_at.asc()).first()

    def list_master_skills(
        self,
        *,
        form_type_key: str | None = None,
        lifecycle_status: MasterSkillLifecycleStatus | str | None = None,
        names: list[str] | None = None,
        loose_only: bool = False,
    ) -> list[MasterSkill]:
        with self._session_factory() as session:
            query = session.query(MasterSkill)
            if form_type_key is not None:
                query = query.filter(MasterSkill.form_type_key == form_type_key)
            if loose_only:
                query = query.filter(MasterSkill.form_type_key.is_(None))
            if lifecycle_status is not None:
                query = query.filter(
                    MasterSkill.lifecycle_status == self._coerce_master_skill_lifecycle_status(lifecycle_status)
                )
            if names:
                normalized_names = [item.strip() for item in names if isinstance(item, str) and item.strip()]
                if normalized_names:
                    query = query.filter(MasterSkill.name.in_(normalized_names))
            return query.order_by(MasterSkill.name.asc(), MasterSkill.created_at.asc()).all()

    def set_master_skill_lifecycle_status(
        self,
        *,
        skill_id: str | None = None,
        name: str | None = None,
        lifecycle_status: MasterSkillLifecycleStatus | str,
    ) -> MasterSkill:
        if not skill_id and not name:
            raise ValueError("skill_id or name is required")

        normalized_lifecycle = self._coerce_master_skill_lifecycle_status(lifecycle_status)
        with self._session_factory() as session:
            query = session.query(MasterSkill)
            if skill_id is not None:
                query = query.filter(MasterSkill.id == skill_id)
            if name is not None:
                query = query.filter(MasterSkill.name == name.strip())
            skill = query.order_by(MasterSkill.created_at.asc()).first()
            if skill is None:
                raise ValueError("master skill not found")
            skill.lifecycle_status = normalized_lifecycle
            session.commit()
            session.refresh(skill)
            return skill

    def upsert_node_skill_assignment(
        self,
        *,
        node_id: str,
        skill_id: str,
        assignment_source: NodeSkillAssignmentSource | str,
        assigned_by_node_id: str | None = None,
    ) -> NodeSkillAssignment:
        normalized_source = self._coerce_node_skill_assignment_source(assignment_source)
        with self._session_factory() as session:
            existing = (
                session.query(NodeSkillAssignment)
                .filter(
                    NodeSkillAssignment.node_id == node_id,
                    NodeSkillAssignment.skill_id == skill_id,
                    NodeSkillAssignment.assignment_source == normalized_source,
                )
                .order_by(NodeSkillAssignment.created_at.asc())
                .first()
            )
            if existing is None:
                existing = NodeSkillAssignment(
                    node_id=node_id,
                    skill_id=skill_id,
                    assignment_source=normalized_source,
                    assigned_by_node_id=assigned_by_node_id,
                )
                session.add(existing)
            else:
                existing.assigned_by_node_id = assigned_by_node_id
            session.commit()
            session.refresh(existing)
            return existing

    def replace_node_skill_assignments_for_source(
        self,
        *,
        node_id: str,
        assignment_source: NodeSkillAssignmentSource | str,
        skill_ids: list[str],
        assigned_by_node_id: str | None = None,
    ) -> list[NodeSkillAssignment]:
        normalized_source = self._coerce_node_skill_assignment_source(assignment_source)
        normalized_skill_ids = sorted({item for item in skill_ids if item})
        with self._session_factory() as session:
            session.query(NodeSkillAssignment).filter(
                NodeSkillAssignment.node_id == node_id,
                NodeSkillAssignment.assignment_source == normalized_source,
            ).delete()
            for skill_id in normalized_skill_ids:
                session.add(
                    NodeSkillAssignment(
                        node_id=node_id,
                        skill_id=skill_id,
                        assignment_source=normalized_source,
                        assigned_by_node_id=assigned_by_node_id,
                    )
                )
            session.commit()
            return (
                session.query(NodeSkillAssignment)
                .filter(
                    NodeSkillAssignment.node_id == node_id,
                    NodeSkillAssignment.assignment_source == normalized_source,
                )
                .order_by(NodeSkillAssignment.created_at.asc(), NodeSkillAssignment.skill_id.asc())
                .all()
            )

    def replace_form_skill_assignments(
        self,
        *,
        form_type_key: str,
        assignments: list[tuple[str, str]],
    ) -> list[NodeSkillAssignment]:
        normalized_form_type_key = form_type_key.strip()
        if not normalized_form_type_key:
            raise ValueError("form_type_key is required")

        deduped_assignments = sorted(
            {(node_id, skill_id) for node_id, skill_id in assignments if node_id and skill_id},
            key=lambda item: (item[0], item[1]),
        )
        with self._session_factory() as session:
            skill_rows = (
                session.query(MasterSkill)
                .filter(MasterSkill.form_type_key == normalized_form_type_key)
                .order_by(MasterSkill.created_at.asc())
                .all()
            )
            form_skill_ids = [item.id for item in skill_rows]
            if form_skill_ids:
                session.query(NodeSkillAssignment).filter(
                    NodeSkillAssignment.skill_id.in_(form_skill_ids),
                    NodeSkillAssignment.assignment_source == NodeSkillAssignmentSource.FORM_STAGE,
                ).delete(synchronize_session=False)
            for node_id, skill_id in deduped_assignments:
                session.add(
                    NodeSkillAssignment(
                        node_id=node_id,
                        skill_id=skill_id,
                        assignment_source=NodeSkillAssignmentSource.FORM_STAGE,
                    )
                )
            session.commit()
            if not form_skill_ids:
                return []
            return (
                session.query(NodeSkillAssignment)
                .filter(
                    NodeSkillAssignment.skill_id.in_(form_skill_ids),
                    NodeSkillAssignment.assignment_source == NodeSkillAssignmentSource.FORM_STAGE,
                )
                .order_by(NodeSkillAssignment.node_id.asc(), NodeSkillAssignment.skill_id.asc())
                .all()
            )

    def delete_node_skill_assignments(
        self,
        *,
        node_id: str,
        skill_ids: list[str] | None = None,
        assignment_source: NodeSkillAssignmentSource | str | None = None,
    ) -> int:
        with self._session_factory() as session:
            query = session.query(NodeSkillAssignment).filter(NodeSkillAssignment.node_id == node_id)
            if skill_ids:
                normalized_skill_ids = [item for item in skill_ids if item]
                if normalized_skill_ids:
                    query = query.filter(NodeSkillAssignment.skill_id.in_(normalized_skill_ids))
            if assignment_source is not None:
                query = query.filter(
                    NodeSkillAssignment.assignment_source == self._coerce_node_skill_assignment_source(assignment_source)
                )
            deleted = query.delete(synchronize_session=False)
            session.commit()
            return int(deleted)

    def list_node_skill_assignments(
        self,
        *,
        node_id: str | None = None,
        skill_id: str | None = None,
        assignment_source: NodeSkillAssignmentSource | str | None = None,
    ) -> list[NodeSkillAssignment]:
        with self._session_factory() as session:
            query = session.query(NodeSkillAssignment)
            if node_id is not None:
                query = query.filter(NodeSkillAssignment.node_id == node_id)
            if skill_id is not None:
                query = query.filter(NodeSkillAssignment.skill_id == skill_id)
            if assignment_source is not None:
                query = query.filter(
                    NodeSkillAssignment.assignment_source == self._coerce_node_skill_assignment_source(assignment_source)
                )
            return query.order_by(
                NodeSkillAssignment.node_id.asc(),
                NodeSkillAssignment.created_at.asc(),
                NodeSkillAssignment.skill_id.asc(),
            ).all()

    def list_node_skill_assignment_details(
        self,
        *,
        node_id: str,
    ) -> list[tuple[NodeSkillAssignment, MasterSkill]]:
        with self._session_factory() as session:
            rows = (
                session.query(NodeSkillAssignment, MasterSkill)
                .join(MasterSkill, MasterSkill.id == NodeSkillAssignment.skill_id)
                .filter(NodeSkillAssignment.node_id == node_id)
                .order_by(MasterSkill.name.asc(), NodeSkillAssignment.assignment_source.asc())
                .all()
            )
            return [(assignment, skill) for assignment, skill in rows]

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
        return self._company_paths.root

    def _load_workspace_form_package(self, *, type_key: str) -> dict[str, Any] | None:
        forms_root = self._company_paths.forms_root
        if not forms_root.exists():
            forms_root = repo_workspace_root() / "forms"
        workflow_path = forms_root / type_key / "workflow.json"
        if not workflow_path.exists():
            return None
        try:
            raw = json.loads(workflow_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        return raw
