from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from omniclaw.budgets.engine import BudgetEngine, BudgetSnapshot
from omniclaw.budgets.schemas import BudgetActionRequest
from omniclaw.config import Settings, load_settings
from omniclaw.db.enums import BudgetMode
from omniclaw.db.models import Node
from omniclaw.db.repository import KernelRepository
from omniclaw.instructions import InstructionsService
from omniclaw.litellm_client import LiteLLMClient

logger = logging.getLogger(__name__)


class BudgetService:
    def __init__(self, repository: KernelRepository, settings: Settings | None = None):
        self._repository = repository
        self._settings = settings or load_settings()
        self._engine = BudgetEngine(repository=repository, settings=self._settings)
        self._instructions = InstructionsService(repository=repository, settings=self._settings)

    async def execute(self, request: BudgetActionRequest) -> dict[str, Any]:
        action = request.action

        if action == "team_budget_view":
            manager = self._resolve_manager_target(request=request)
            actor = self._resolve_actor(request=request, required=False)
            if actor is not None and actor.id != manager.id:
                raise HTTPException(status_code=403, detail="actor may only view its own team budget")
            return self._engine.build_team_view(manager=manager)

        if action == "set_team_allocations":
            manager = self._resolve_manager_target(request=request)
            actor = self._resolve_actor(request=request, required=True)
            if actor.id != manager.id:
                raise HTTPException(status_code=403, detail="actor may only update its own direct team allocations")
            if not request.allocations:
                raise HTTPException(status_code=422, detail="allocations are required")

            normalized_allocations = self._resolve_allocations(request=request)
            pre_children = self._capture_direct_child_state(manager=manager)
            saved_allocations = self._engine.replace_team_allocations(
                manager=manager,
                allocations=normalized_allocations,
            )
            async with self._maybe_client() as client:
                _, _, snapshots, sync_result = await self._engine.recalculate_company_budget(
                    client=client,
                    force_root_free=True,
                )
            notifications = self._notify_direct_reports(
                manager=manager,
                snapshots=snapshots,
                previous_state=pre_children,
                reason=request.reason,
                impact_summary=request.impact_summary,
            )
            render = self._instructions.sync_all_active_agents()
            return {
                "action": "set_team_allocations",
                "manager": {"id": manager.id, "name": manager.name},
                "allocations": saved_allocations,
                "team": self._engine.build_team_view(manager=manager),
                "notifications": notifications,
                "synced_caps": sync_result.synced_count,
                "sync_errors": sync_result.errors,
                "instructions_render": render["summary"],
            }

        if action == "set_node_budget_mode":
            node = self._resolve_target_node(request=request)
            actor = self._resolve_actor(request=request, required=False)
            if actor is not None and actor.id not in {node.id, self._manager_id(node)}:
                raise HTTPException(status_code=403, detail="actor may only update self or direct-report budget mode")
            if not request.budget_mode:
                raise HTTPException(status_code=422, detail="budget_mode is required")
            budget_mode = self._coerce_budget_mode(request.budget_mode)
            updated_budget = self._engine.set_node_budget_mode(node=node, budget_mode=budget_mode)
            async with self._maybe_client() as client:
                _, _, _, sync_result = await self._engine.recalculate_company_budget(
                    client=client,
                    force_root_free=True,
                )
            render = self._instructions.sync_all_active_agents()
            return {
                "action": "set_node_budget_mode",
                "node": {"id": node.id, "name": node.name},
                "budget": self._serialize_budget(updated_budget, node=node),
                "synced_caps": sync_result.synced_count,
                "sync_errors": sync_result.errors,
                "instructions_render": render["summary"],
            }

        if action == "run_budget_cycle":
            cycle_date = self._parse_cycle_date(request.cycle_date)
            result = await self._run_budget_cycle(cycle_date=cycle_date, force=request.break_glass)
            return result

        if action == "recalculate_subtree":
            async with self._maybe_client() as client:
                _, _, _, sync_result = await self._engine.recalculate_company_budget(
                    client=client,
                    force_root_free=True,
                )
            render = self._instructions.sync_all_active_agents()
            target = self._resolve_target_node(request=request) if request.node_id or request.node_name else None
            response = {
                "action": "recalculate_subtree",
                "status": "ok",
                "synced_caps": sync_result.synced_count,
                "sync_errors": sync_result.errors,
                "instructions_render": render["summary"],
            }
            if target is not None:
                response["team"] = self._engine.build_team_view(manager=target)
            return response

        if action == "budget_report":
            return self.build_budget_report()

        async with self._require_client() as client:
            if action == "sync_node_cost":
                return await self._sync_node_cost(request, client)
            if action == "sync_all_costs":
                return await self._sync_all_costs(client)
            if action == "update_node_allowance":
                return await self._update_node_allowance(request, client)
            raise HTTPException(status_code=400, detail=f"Unsupported budget action '{action}'")

    async def run_due_cycle(self) -> dict[str, Any] | None:
        due_date = self._engine.due_cycle_date()
        if due_date is None:
            return None
        return await self._run_budget_cycle(cycle_date=due_date, force=False)

    async def _run_budget_cycle(self, *, cycle_date: date | None, force: bool) -> dict[str, Any]:
        async with self._maybe_client() as client:
            result = await self._engine.run_budget_cycle(client=client, cycle_date=cycle_date, force=force)
        render = self._instructions.sync_all_active_agents()
        result["instructions_render"] = render["summary"]
        return result

    async def _sync_node_cost(self, request: BudgetActionRequest, client: LiteLLMClient) -> dict[str, Any]:
        node = self._resolve_target_node(request=request)
        budget = self._repository.get_budget(node_id=node.id)
        if not budget or not budget.virtual_api_key:
            raise HTTPException(status_code=404, detail=f"No LiteLLM virtual key associated with node '{node.name}'")
        if budget.budget_mode == BudgetMode.FREE:
            raise HTTPException(status_code=409, detail=f"Node '{node.name}' is in free mode and has no enforced cap")

        info = await client.get_user_info(user_id=node.name)
        spend = Decimal(str(info.get("spend", 0.0)))
        updated_budget = self._repository.upsert_budget(
            node_id=node.id,
            current_spend=spend,
        )
        return {
            "action": "sync_node_cost",
            "node": {"id": node.id, "name": node.name},
            "budget": self._serialize_budget(updated_budget, node=node),
            "provider_max_budget_usd": info.get("max_budget"),
        }

    async def _sync_all_costs(self, client: LiteLLMClient) -> dict[str, Any]:
        synced = 0
        errors: list[dict[str, str]] = []
        for node in self._repository.list_active_agent_nodes_with_workspaces():
            try:
                budget = self._repository.get_budget(node_id=node.id)
                if not budget or not budget.virtual_api_key or budget.budget_mode == BudgetMode.FREE:
                    continue
                info = await client.get_user_info(user_id=node.name)
                spend = Decimal(str(info.get("spend", 0.0)))
                self._repository.upsert_budget(node_id=node.id, current_spend=spend)
                synced += 1
            except Exception as exc:  # pragma: no cover - defensive aggregation
                logger.error("Failed to sync cost for node %s: %s", node.name, exc)
                errors.append({"node_name": node.name, "error": str(exc)})
        return {
            "action": "sync_all_costs",
            "synced_count": synced,
            "errors": errors,
        }

    async def _update_node_allowance(self, request: BudgetActionRequest, client: LiteLLMClient) -> dict[str, Any]:
        if request.new_daily_limit_usd is None:
            raise HTTPException(status_code=422, detail="new_daily_limit_usd is required")
        node = self._resolve_target_node(request=request)
        budget = self._repository.get_budget(node_id=node.id)
        if budget is None:
            raise HTTPException(status_code=404, detail=f"No budget row exists for node '{node.name}'")
        if not request.break_glass and budget.parent_node_id is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Node '{node.name}' is hierarchy-managed; use set_team_allocations or break_glass=true",
            )
        if not budget.virtual_api_key:
            raise HTTPException(status_code=404, detail=f"No LiteLLM virtual key associated with node '{node.name}'")

        updated_info = await client.update_user_budget(
            user_id=node.name,
            max_budget=request.new_daily_limit_usd,
        )
        updated_budget = self._repository.upsert_budget(
            node_id=node.id,
            daily_limit_usd=Decimal(str(request.new_daily_limit_usd)),
            current_daily_allowance=Decimal(str(request.new_daily_limit_usd)),
            rollover_reserve_usd=Decimal("0.00"),
        )
        render = self._instructions.sync_all_active_agents()
        return {
            "action": "update_node_allowance",
            "node": {"id": node.id, "name": node.name},
            "budget": self._serialize_budget(updated_budget, node=node),
            "litellm_response": updated_info,
            "instructions_render": render["summary"],
        }

    def build_budget_report(self) -> dict[str, Any]:
        config, root_node, snapshots = self._engine.compute_company_snapshots()
        allocations = self._repository.list_budget_allocations()
        node_lookup = {node.id: node for node in self._repository.list_agent_nodes()}
        allocation_map = {item.child_node_id: item for item in allocations}
        rows: list[dict[str, Any]] = []
        metered_total = Decimal("0.00")
        spend_total = Decimal("0.00")
        for node in node_lookup.values():
            snapshot = snapshots.get(node.id)
            if snapshot is None:
                budget = self._repository.get_budget(node_id=node.id)
                if budget is None:
                    continue
                snapshot = self._engine._snapshot_from_budget(
                    node=node,
                    budget=budget,
                    incoming_pool_usd=Decimal(str(budget.current_daily_allowance)),
                )
            manager = self._repository.get_manager_node(child_node_id=node.id)
            budget = self._repository.get_budget(node_id=node.id)
            row = self._engine._serialize_snapshot(snapshot)
            row.update(
                {
                    "manager_node_id": manager.id if manager else None,
                    "manager_name": manager.name if manager else None,
                    "gateway_running": bool(node.gateway_running),
                    "provider": "litellm" if budget and budget.virtual_api_key else None,
                    "has_virtual_api_key": bool(budget and budget.virtual_api_key),
                }
            )
            rows.append(row)
            spend_total += Decimal(str(snapshot.current_spend_usd))
            if snapshot.budget_mode == BudgetMode.METERED:
                metered_total += Decimal(str(snapshot.remaining_budget_usd))

        return {
            "action": "budget_report",
            "company_budget": {
                "daily_company_budget_usd": float(config.daily_company_budget_usd),
                "root_allocator_node": root_node.name,
                "reset_time_utc": config.reset_time_utc,
                "current_total_spend_usd": float(spend_total),
                "remaining_metered_budget_usd": float(metered_total),
            },
            "allocations": [
                {
                    "manager_node_id": item.manager_node_id,
                    "manager_name": node_lookup[item.manager_node_id].name if item.manager_node_id in node_lookup else None,
                    "child_node_id": item.child_node_id,
                    "child_node_name": node_lookup[item.child_node_id].name if item.child_node_id in node_lookup else None,
                    "percentage": float(item.percentage),
                }
                for item in allocations
            ],
            "rows": rows,
        }

    def _notify_direct_reports(
        self,
        *,
        manager: Node,
        snapshots: dict[str, BudgetSnapshot],
        previous_state: dict[str, tuple[Decimal, Decimal]],
        reason: str | None,
        impact_summary: str | None,
    ) -> list[dict[str, Any]]:
        notifications: list[dict[str, Any]] = []
        issued_at = datetime.now(timezone.utc)
        for child in self._repository.list_child_nodes(parent_node_id=manager.id):
            snapshot = snapshots.get(child.id)
            if snapshot is None:
                continue
            previous_allowance, previous_available = previous_state.get(
                child.id,
                (Decimal("0.00"), Decimal("0.00")),
            )
            changed = (
                previous_allowance != snapshot.self_daily_allowance_usd
                or previous_available != snapshot.available_budget_usd
            )
            if not changed:
                continue

            has_subordinates = bool(self._repository.list_child_nodes(parent_node_id=child.id))
            if has_subordinates:
                self._repository.upsert_budget(
                    node_id=child.id,
                    review_required_at=issued_at,
                )

            path = self._write_budget_change_message(
                manager=manager,
                child=child,
                snapshot=snapshot,
                reason=reason,
                impact_summary=impact_summary,
                review_required=has_subordinates,
            )
            notifications.append(
                {
                    "node": child.name,
                    "path": path,
                    "review_required": has_subordinates,
                }
            )
        return notifications

    def _write_budget_change_message(
        self,
        *,
        manager: Node,
        child: Node,
        snapshot: BudgetSnapshot,
        reason: str | None,
        impact_summary: str | None,
        review_required: bool,
    ) -> str | None:
        if not child.workspace_root:
            return None
        inbox_dir = Path(child.workspace_root) / self._settings.ipc_inbox_new_rel
        inbox_dir.mkdir(parents=True, exist_ok=True)
        slug = f"budget-update-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.md"
        target_path = self._unique_path(inbox_dir / slug)
        review_line = (
            "You manage downstream agents. Reapply your direct-report allocations and explain the change to your team."
            if review_required
            else "No downstream reallocation is required."
        )
        remaining_line = (
            "Unlimited provider use in free mode."
            if snapshot.budget_mode == BudgetMode.FREE
            else f"Remaining enforced budget: ${snapshot.remaining_budget_usd:.2f}"
        )
        content = (
            "---\n"
            "type: MESSAGE\n"
            "sender: Kernel_Budget\n"
            f"target: {child.name}\n"
            f"subject: Budget update from {manager.name}\n"
            "---\n\n"
            "# Budget Update\n\n"
            f"- Manager: {manager.name}\n"
            f"- Mode: {snapshot.budget_mode.value}\n"
            f"- Daily self allowance: ${snapshot.self_daily_allowance_usd:.2f}\n"
            f"- Reserve carried: ${snapshot.rollover_reserve_usd:.2f}\n"
            f"- Available controlled budget: ${snapshot.available_budget_usd:.2f}\n"
            f"- {remaining_line}\n"
            f"- Reason: {reason or 'No explicit reason provided.'}\n"
            f"- Expected impact: {impact_summary or 'Budget distribution changed upstream.'}\n\n"
            f"{review_line}\n"
        )
        target_path.write_text(content, encoding="utf-8")
        return str(target_path.resolve())

    def _capture_direct_child_state(self, *, manager: Node) -> dict[str, tuple[Decimal, Decimal]]:
        state: dict[str, tuple[Decimal, Decimal]] = {}
        for child in self._repository.list_child_nodes(parent_node_id=manager.id):
            budget = self._repository.get_budget(node_id=child.id)
            if budget is None:
                state[child.id] = (Decimal("0.00"), Decimal("0.00"))
            else:
                state[child.id] = (
                    Decimal(str(budget.current_daily_allowance)),
                    Decimal(str(budget.daily_limit_usd)),
                )
        return state

    def _resolve_allocations(self, *, request: BudgetActionRequest) -> list[tuple[Node, Decimal]]:
        resolved: list[tuple[Node, Decimal]] = []
        assert request.allocations is not None
        for item in request.allocations:
            node = self._repository.get_node(node_id=item.child_node_id, node_name=item.child_node_name)
            if node is None:
                raise HTTPException(status_code=404, detail="allocation child node not found")
            resolved.append((node, Decimal(str(item.percentage)).quantize(Decimal("0.01"))))
        return resolved

    def _resolve_manager_target(self, *, request: BudgetActionRequest) -> Node:
        actor = self._resolve_actor(request=request, required=False)
        if request.node_id or request.node_name:
            node = self._resolve_target_node(request=request)
        elif actor is not None:
            node = actor
        else:
            raise HTTPException(status_code=422, detail="actor_node_id/actor_node_name or node_id/node_name is required")
        if not self._repository.list_child_nodes(parent_node_id=node.id):
            raise HTTPException(status_code=422, detail=f"node '{node.name}' has no direct reports")
        return node

    def _resolve_target_node(self, *, request: BudgetActionRequest) -> Node:
        node = self._repository.get_node(node_id=request.node_id, node_name=request.node_name)
        if node is None:
            raise HTTPException(status_code=404, detail="Target node not found")
        return node

    def _resolve_actor(self, *, request: BudgetActionRequest, required: bool) -> Node | None:
        if not request.actor_node_id and not request.actor_node_name:
            if required:
                raise HTTPException(status_code=422, detail="actor_node_id or actor_node_name is required")
            return None
        actor = self._repository.get_node(node_id=request.actor_node_id, node_name=request.actor_node_name)
        if actor is None:
            raise HTTPException(status_code=404, detail="actor node not found")
        return actor

    def _serialize_budget(self, budget: Any, *, node: Node) -> dict[str, Any]:
        return {
            "node_name": node.name,
            "budget_mode": budget.budget_mode.value,
            "virtual_api_key": budget.virtual_api_key,
            "current_spend": float(budget.current_spend),
            "daily_limit_usd": float(budget.daily_limit_usd),
            "current_daily_allowance": float(budget.current_daily_allowance),
            "rollover_reserve_usd": float(budget.rollover_reserve_usd),
            "review_required_at": budget.review_required_at.isoformat() if budget.review_required_at else None,
        }

    @staticmethod
    def _parse_cycle_date(raw_value: str | None) -> date | None:
        if raw_value is None:
            return None
        try:
            return date.fromisoformat(raw_value)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="cycle_date must be YYYY-MM-DD") from exc

    @staticmethod
    def _coerce_budget_mode(raw_mode: str) -> BudgetMode:
        try:
            return BudgetMode(raw_mode.strip().lower())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Unsupported budget mode '{raw_mode}'") from exc

    def _manager_id(self, node: Node) -> str | None:
        manager = self._repository.get_manager_node(child_node_id=node.id)
        if manager is None:
            return None
        return manager.id

    async def _close_client(self, client: LiteLLMClient | None) -> None:
        if client is not None:
            await client.close()

    def _unique_path(self, path: Path) -> Path:
        if not path.exists():
            return path
        for index in range(1, 1000):
            candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
            if not candidate.exists():
                return candidate
        raise RuntimeError(f"unable to find unique path for {path}")

    async def _client_or_none(self) -> LiteLLMClient | None:
        if not self._settings.litellm_proxy_url or not self._settings.litellm_master_key:
            return None
        return LiteLLMClient(
            proxy_url=self._settings.litellm_proxy_url,
            master_key=self._settings.litellm_master_key,
        )

    async def __aenter_client(self, required: bool) -> LiteLLMClient | None:
        client = await self._client_or_none()
        if client is None and required:
            raise HTTPException(
                status_code=503,
                detail="LiteLLM proxy URL and master key are not configured in settings.",
            )
        return client

    @asynccontextmanager
    async def _maybe_client(self):
        client = await self.__aenter_client(required=False)
        try:
            yield client
        finally:
            await self._close_client(client)

    @asynccontextmanager
    async def _require_client(self):
        client = await self.__aenter_client(required=True)
        try:
            yield client
        finally:
            await self._close_client(client)
