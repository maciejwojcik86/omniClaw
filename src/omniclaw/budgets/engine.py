from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException

from omniclaw.config import Settings, load_effective_company_settings
from omniclaw.db.enums import BudgetMode, NodeType
from omniclaw.db.models import Budget, Node
from omniclaw.db.repository import KernelRepository
from omniclaw.litellm_client import LiteLLMClient


_CENT = Decimal("0.000001")


def _quantize(value: Decimal | float | int) -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class CompanyBudgetConfig:
    daily_company_budget_usd: Decimal
    root_allocator_node: str
    reset_time_utc: str


@dataclass(frozen=True)
class BudgetSnapshot:
    node: Node
    budget_mode: BudgetMode
    parent_node_id: str | None
    allocated_percentage: Decimal | None
    incoming_pool_usd: Decimal
    self_daily_allowance_usd: Decimal
    rollover_reserve_usd: Decimal
    available_budget_usd: Decimal
    current_spend_usd: Decimal
    remaining_budget_usd: Decimal
    review_required_at: datetime | None


@dataclass(frozen=True)
class CapSyncResult:
    synced_count: int
    errors: list[dict[str, str]]


class BudgetEngine:
    def __init__(self, *, repository: KernelRepository, settings: Settings):
        self._repository = repository
        self._settings = settings

    def load_company_budget_config(self) -> CompanyBudgetConfig:
        payload = load_effective_company_settings(self._settings)
        raw_budgeting = payload.get("budgeting")
        if not isinstance(raw_budgeting, Mapping):
            raise HTTPException(status_code=503, detail="Company budgeting config is missing")

        raw_daily_budget = raw_budgeting.get("daily_company_budget_usd")
        raw_root = raw_budgeting.get("root_allocator_node")
        raw_reset_time = raw_budgeting.get("reset_time_utc")

        if raw_daily_budget is None or raw_root is None or raw_reset_time is None:
            raise HTTPException(status_code=503, detail="Company budgeting config is incomplete")

        return CompanyBudgetConfig(
            daily_company_budget_usd=_quantize(Decimal(str(raw_daily_budget))),
            root_allocator_node=str(raw_root).strip(),
            reset_time_utc=str(raw_reset_time).strip(),
        )

    def compute_company_snapshots(self) -> tuple[CompanyBudgetConfig, Node, dict[str, BudgetSnapshot]]:
        config = self.load_company_budget_config()
        root_node = self._resolve_root_allocator(config)
        snapshots = self._build_snapshot_tree(
            node=root_node,
            gross_inflow=config.daily_company_budget_usd,
            parent_node_id=None,
            allocated_percentage=None,
            reset_cycle=False,
            force_root_free=True,
        )
        return config, root_node, snapshots

    async def run_budget_cycle(
        self,
        *,
        client: LiteLLMClient | None = None,
        cycle_date: date | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        config = self.load_company_budget_config()
        root_node = self._resolve_root_allocator(config)
        resolved_cycle_date = cycle_date or datetime.now(timezone.utc).date()
        existing_cycle = self._repository.get_budget_cycle(cycle_date=resolved_cycle_date)
        if existing_cycle is not None and not force:
            snapshots = self._build_snapshot_tree(
                node=root_node,
                gross_inflow=config.daily_company_budget_usd,
                parent_node_id=None,
                allocated_percentage=None,
                reset_cycle=False,
                force_root_free=False,
            )
            return {
                "action": "run_budget_cycle",
                "status": "already_ran",
                "cycle": {
                    "cycle_date": resolved_cycle_date.isoformat(),
                    "company_budget_usd": float(existing_cycle.company_budget_usd),
                    "executed_at": existing_cycle.executed_at.isoformat(),
                },
                "synced_caps": 0,
                "snapshot_count": len(snapshots),
            }

        snapshots = self._build_snapshot_tree(
            node=root_node,
            gross_inflow=config.daily_company_budget_usd,
            parent_node_id=None,
            allocated_percentage=None,
            reset_cycle=True,
            force_root_free=True,
        )
        cycle = self._repository.upsert_budget_cycle(
            cycle_date=resolved_cycle_date,
            company_budget_usd=config.daily_company_budget_usd,
            root_allocator_node_id=root_node.id,
            executed_at=datetime.now(timezone.utc),
        )
        sync_result = await self.sync_metered_caps(client=client, snapshots=snapshots)
        return {
            "action": "run_budget_cycle",
            "status": "ok",
            "cycle": {
                "cycle_date": cycle.cycle_date.isoformat(),
                "company_budget_usd": float(cycle.company_budget_usd),
                "executed_at": cycle.executed_at.isoformat(),
            },
            "synced_caps": sync_result.synced_count,
            "sync_errors": sync_result.errors,
            "snapshot_count": len(snapshots),
        }

    async def recalculate_company_budget(
        self,
        *,
        client: LiteLLMClient | None = None,
        force_root_free: bool = False,
    ) -> tuple[CompanyBudgetConfig, Node, dict[str, BudgetSnapshot], CapSyncResult]:
        config = self.load_company_budget_config()
        root_node = self._resolve_root_allocator(config)
        snapshots = self._build_snapshot_tree(
            node=root_node,
            gross_inflow=config.daily_company_budget_usd,
            parent_node_id=None,
            allocated_percentage=None,
            reset_cycle=False,
            force_root_free=force_root_free,
        )
        sync_result = await self.sync_metered_caps(client=client, snapshots=snapshots)
        return config, root_node, snapshots, sync_result

    async def sync_metered_caps(
        self,
        *,
        client: LiteLLMClient | None,
        snapshots: dict[str, BudgetSnapshot],
    ) -> CapSyncResult:
        if client is None:
            return CapSyncResult(synced_count=0, errors=[])

        synced = 0
        errors: list[dict[str, str]] = []
        for snapshot in snapshots.values():
            if snapshot.budget_mode != BudgetMode.METERED:
                continue
            budget = self._repository.get_budget(node_id=snapshot.node.id)
            if budget is None or not budget.virtual_api_key:
                continue
            try:
                await client.update_user_budget(
                    user_id=snapshot.node.name,
                    max_budget=float(snapshot.available_budget_usd),
                )
                synced += 1
            except Exception as exc:  # pragma: no cover - defensive live-path tolerance
                errors.append(
                    {
                        "node_name": snapshot.node.name,
                        "error": str(exc),
                    }
                )
        return CapSyncResult(synced_count=synced, errors=errors)

    def due_cycle_date(self) -> date | None:
        config = self.load_company_budget_config()
        now = datetime.now(timezone.utc)
        reset_time = self._parse_reset_time(config.reset_time_utc)
        if now.time() < reset_time:
            return None
        today = now.date()
        if self._repository.get_budget_cycle(cycle_date=today) is not None:
            return None
        return today

    def build_team_view(self, *, manager: Node) -> dict[str, Any]:
        config, root_node, snapshots = self.compute_company_snapshots()
        manager_snapshot = snapshots.get(manager.id)
        if manager_snapshot is None:
            budget = self._ensure_budget(manager, parent_node_id=self._manager_id_for_node(manager))
            manager_snapshot = self._snapshot_from_budget(
                node=manager,
                budget=budget,
                incoming_pool_usd=budget.current_daily_allowance,
            )

        rows = [self._serialize_snapshot(manager_snapshot)]
        for child in self._repository.list_child_nodes(parent_node_id=manager.id):
            child_snapshot = snapshots.get(child.id)
            if child_snapshot is None:
                child_budget = self._ensure_budget(child, parent_node_id=manager.id)
                child_snapshot = self._snapshot_from_budget(
                    node=child,
                    budget=child_budget,
                    incoming_pool_usd=child_budget.current_daily_allowance,
                )
            rows.append(self._serialize_snapshot(child_snapshot))

        return {
            "action": "team_budget_view",
            "manager": {
                "id": manager.id,
                "name": manager.name,
                "type": manager.type.value,
            },
            "company_budget": {
                "daily_company_budget_usd": float(config.daily_company_budget_usd),
                "root_allocator_node": root_node.name,
                "reset_time_utc": config.reset_time_utc,
            },
            "rows": rows,
        }

    def set_node_budget_mode(self, *, node: Node, budget_mode: BudgetMode) -> Budget:
        existing_budget = self._repository.get_budget(node_id=node.id)
        parent_node_id = existing_budget.parent_node_id if existing_budget is not None else self._manager_id_for_node(node)
        return self._repository.upsert_budget(
            node_id=node.id,
            parent_node_id=parent_node_id,
            budget_mode=budget_mode,
        )

    def replace_team_allocations(
        self,
        *,
        manager: Node,
        allocations: list[tuple[Node, Decimal]],
    ) -> list[dict[str, Any]]:
        self._validate_direct_children(manager=manager, allocations=allocations)
        stored = self._repository.replace_budget_allocations(
            manager_node_id=manager.id,
            allocations=[(node.id, float(percentage)) for node, percentage in allocations],
        )
        self._repository.upsert_budget(
            node_id=manager.id,
            parent_node_id=self._manager_id_for_node(manager),
            review_required_at=None,
        )
        return [
            {
                "child_node_id": item.child_node_id,
                "percentage": float(item.percentage),
            }
            for item in stored
        ]

    def build_direct_team_summary(self, *, node: Node) -> str:
        try:
            _, _, snapshots = self.compute_company_snapshots()
        except HTTPException:
            snapshots = {}

        children = self._repository.list_child_nodes(parent_node_id=node.id)
        if not children:
            return "No direct team budget allocations."

        lines: list[str] = []
        for child in children:
            snapshot = snapshots.get(child.id)
            if snapshot is None:
                budget = self._ensure_budget(child, parent_node_id=node.id)
                snapshot = self._snapshot_from_budget(
                    node=child,
                    budget=budget,
                    incoming_pool_usd=budget.current_daily_allowance,
                )
            remaining = self._format_budget_remaining(snapshot)
            lines.append(
                f"- {child.name} | {snapshot.budget_mode.value} | "
                f"inflow ${snapshot.self_daily_allowance_usd:.2f} | reserve ${snapshot.rollover_reserve_usd:.2f} | {remaining}"
            )
        return "\n".join(lines)

    def review_required_notice(self, *, node: Node) -> str:
        budget = self._repository.get_budget(node_id=node.id)
        if budget is None or budget.review_required_at is None:
            return "No budget review required."
        return (
            "Budget review required. Your incoming department budget changed and you must "
            "reapply your direct-report allocations before messaging changes downward."
        )

    def build_budget_placeholders(self, *, node: Node) -> dict[str, str]:
        try:
            _, _, snapshots = self.compute_company_snapshots()
        except HTTPException:
            snapshots = {}
        budget = self._ensure_budget(node, parent_node_id=self._manager_id_for_node(node))
        snapshot = snapshots.get(node.id) or self._snapshot_from_budget(
            node=node,
            budget=budget,
            incoming_pool_usd=budget.current_daily_allowance,
        )
        remaining = self._format_budget_remaining(snapshot)
        return {
            "budget.mode": snapshot.budget_mode.value,
            "budget.daily_inflow_usd": f"{snapshot.self_daily_allowance_usd:.2f}",
            "budget.rollover_reserve_usd": f"{snapshot.rollover_reserve_usd:.2f}",
            "budget.remaining_usd": remaining,
            "budget.review_required_notice": self.review_required_notice(node=node),
            "budget.direct_team_summary": self.build_direct_team_summary(node=node),
        }

    def _build_snapshot_tree(
        self,
        *,
        node: Node,
        gross_inflow: Decimal,
        parent_node_id: str | None,
        allocated_percentage: Decimal | None,
        reset_cycle: bool,
        force_root_free: bool,
    ) -> dict[str, BudgetSnapshot]:
        budget = self._ensure_budget(node, parent_node_id=parent_node_id)
        if force_root_free and parent_node_id is None and budget.budget_mode != BudgetMode.FREE:
            budget = self._repository.upsert_budget(
                node_id=node.id,
                budget_mode=BudgetMode.FREE,
                parent_node_id=None,
            )

        reserve = _quantize(budget.rollover_reserve_usd)
        current_spend = _quantize(budget.current_spend)
        if budget.budget_mode == BudgetMode.METERED and not reset_cycle:
            reconciled_spend = _quantize(self._repository.sum_agent_llm_costs(node_id=node.id))
            if reconciled_spend != current_spend:
                budget = self._repository.upsert_budget(node_id=node.id, current_spend=reconciled_spend)
                current_spend = reconciled_spend
        if reset_cycle:
            reserve = max(_quantize(budget.daily_limit_usd) - current_spend, Decimal("0.00"))
            current_spend = Decimal("0.00")

        children = self._repository.list_child_nodes(parent_node_id=node.id)
        allocation_map = {
            item.child_node_id: _quantize(item.percentage)
            for item in self._repository.list_budget_allocations(manager_node_id=node.id)
        }
        allocated_children = [
            (child, allocation_map.get(child.id, Decimal("0.00")))
            for child in children
            if allocation_map.get(child.id, Decimal("0.00")) > 0
        ]
        total_allocated_percentage = sum((percentage for _, percentage in allocated_children), Decimal("0.00"))

        remaining_pool = _quantize(gross_inflow)
        child_gross_values: dict[str, Decimal] = {}
        for index, (child, percentage) in enumerate(allocated_children):
            if index == len(allocated_children) - 1 and total_allocated_percentage == Decimal("100.00"):
                child_gross = remaining_pool
            else:
                child_gross = _quantize((gross_inflow * percentage) / Decimal("100"))
                if child_gross > remaining_pool:
                    child_gross = remaining_pool
            remaining_pool = _quantize(remaining_pool - child_gross)
            child_gross_values[child.id] = child_gross

        self_allowance = max(remaining_pool, Decimal("0.00"))
        available_budget = _quantize(self_allowance + reserve)
        remaining_budget = max(_quantize(available_budget - current_spend), Decimal("0.00"))

        persisted = self._repository.upsert_budget(
            node_id=node.id,
            daily_limit_usd=available_budget,
            current_daily_allowance=self_allowance,
            current_spend=current_spend,
            parent_node_id=parent_node_id,
            allocated_percentage=float(allocated_percentage) if allocated_percentage is not None else None,
            rollover_reserve_usd=reserve,
            review_required_at=budget.review_required_at,
        )
        snapshot = BudgetSnapshot(
            node=node,
            budget_mode=persisted.budget_mode,
            parent_node_id=parent_node_id,
            allocated_percentage=allocated_percentage,
            incoming_pool_usd=_quantize(gross_inflow),
            self_daily_allowance_usd=self_allowance,
            rollover_reserve_usd=reserve,
            available_budget_usd=available_budget,
            current_spend_usd=current_spend,
            remaining_budget_usd=remaining_budget,
            review_required_at=persisted.review_required_at,
        )

        results = {node.id: snapshot}
        for child in children:
            child_percentage = allocation_map.get(child.id)
            child_gross = child_gross_values.get(child.id, Decimal("0.00"))
            if child_percentage is None:
                child_percentage = Decimal("0.00")
            results.update(
                self._build_snapshot_tree(
                    node=child,
                    gross_inflow=child_gross,
                    parent_node_id=node.id,
                    allocated_percentage=child_percentage,
                    reset_cycle=reset_cycle,
                    force_root_free=False,
                )
            )
        return results

    def _ensure_budget(self, node: Node, *, parent_node_id: str | None) -> Budget:
        budget = self._repository.get_budget(node_id=node.id)
        if budget is None:
            default_mode = BudgetMode.METERED if node.type == NodeType.AGENT else BudgetMode.FREE
            budget = self._repository.upsert_budget(
                node_id=node.id,
                parent_node_id=parent_node_id,
                budget_mode=default_mode,
            )
        elif parent_node_id != budget.parent_node_id:
            budget = self._repository.upsert_budget(
                node_id=node.id,
                parent_node_id=parent_node_id,
            )
        return budget

    def _resolve_root_allocator(self, config: CompanyBudgetConfig) -> Node:
        node, error = self._repository.resolve_unique_node_reference(config.root_allocator_node)
        if node is None:
            raise HTTPException(status_code=404, detail=error or "root allocator node not found")
        return node

    def _validate_direct_children(
        self,
        *,
        manager: Node,
        allocations: list[tuple[Node, Decimal]],
    ) -> None:
        direct_children = {child.id for child in self._repository.list_child_nodes(parent_node_id=manager.id)}
        seen: set[str] = set()
        total = Decimal("0.00")
        for child, percentage in allocations:
            if child.id not in direct_children:
                raise HTTPException(
                    status_code=403,
                    detail=f"node '{child.name}' is not a direct report of '{manager.name}'",
                )
            if child.id in seen:
                raise HTTPException(status_code=422, detail=f"duplicate allocation for '{child.name}'")
            seen.add(child.id)
            if percentage < Decimal("0.00"):
                raise HTTPException(status_code=422, detail="allocation percentage cannot be negative")
            total += percentage
        if total > Decimal("100.00"):
            raise HTTPException(status_code=422, detail="allocation percentages cannot exceed 100")

    def _serialize_snapshot(self, snapshot: BudgetSnapshot) -> dict[str, Any]:
        return {
            "node": {
                "id": snapshot.node.id,
                "name": snapshot.node.name,
                "type": snapshot.node.type.value,
            },
            "budget_mode": snapshot.budget_mode.value,
            "allocated_percentage": float(snapshot.allocated_percentage) if snapshot.allocated_percentage is not None else None,
            "incoming_pool_usd": float(snapshot.incoming_pool_usd),
            "daily_inflow_usd": float(snapshot.self_daily_allowance_usd),
            "rollover_reserve_usd": float(snapshot.rollover_reserve_usd),
            "available_budget_usd": float(snapshot.available_budget_usd),
            "effective_cap_usd": float(snapshot.available_budget_usd) if snapshot.budget_mode == BudgetMode.METERED else None,
            "current_spend": float(snapshot.current_spend_usd),
            "remaining_budget_usd": float(snapshot.remaining_budget_usd) if snapshot.budget_mode == BudgetMode.METERED else None,
            "review_required": snapshot.review_required_at is not None,
            "review_required_at": snapshot.review_required_at.isoformat() if snapshot.review_required_at else None,
        }

    def _snapshot_from_budget(
        self,
        *,
        node: Node,
        budget: Budget,
        incoming_pool_usd: Decimal,
    ) -> BudgetSnapshot:
        available_budget = _quantize(budget.daily_limit_usd)
        current_spend = _quantize(budget.current_spend)
        return BudgetSnapshot(
            node=node,
            budget_mode=budget.budget_mode,
            parent_node_id=budget.parent_node_id,
            allocated_percentage=budget.allocated_percentage,
            incoming_pool_usd=_quantize(incoming_pool_usd),
            self_daily_allowance_usd=_quantize(budget.current_daily_allowance),
            rollover_reserve_usd=_quantize(budget.rollover_reserve_usd),
            available_budget_usd=available_budget,
            current_spend_usd=current_spend,
            remaining_budget_usd=max(_quantize(available_budget - current_spend), Decimal("0.00")),
            review_required_at=budget.review_required_at,
        )

    def _format_budget_remaining(self, snapshot: BudgetSnapshot) -> str:
        if snapshot.budget_mode == BudgetMode.FREE:
            return f"reserve ${snapshot.rollover_reserve_usd:.2f} (free mode)"
        return f"remaining ${snapshot.remaining_budget_usd:.2f}"

    def _manager_id_for_node(self, node: Node) -> str | None:
        manager = self._repository.get_manager_node(child_node_id=node.id)
        if manager is None:
            return None
        return manager.id

    @staticmethod
    def _parse_reset_time(raw_value: str) -> time:
        try:
            hour_str, minute_str = raw_value.split(":", 1)
            return time(hour=int(hour_str), minute=int(minute_str))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=503, detail="Invalid reset_time_utc in company config") from exc
