from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class BudgetAllocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_node_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("child_node_id", "node_id"),
    )
    child_node_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("child_node_name", "agent_name", "node_name"),
    )
    percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        validation_alias=AliasChoices("percentage", "share_percent", "share_percentage", "percent"),
    )

    @model_validator(mode="after")
    def validate_child_reference(self) -> "BudgetAllocationInput":
        if not self.child_node_id and not self.child_node_name:
            raise ValueError("child_node_id or child_node_name is required")
        return self


class BudgetActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "sync_all_costs",
        "sync_node_cost",
        "update_node_allowance",
        "team_budget_view",
        "set_team_allocations",
        "set_node_budget_mode",
        "run_budget_cycle",
        "recalculate_subtree",
        "budget_report",
    ]
    actor_node_id: str | None = None
    actor_node_name: str | None = None
    node_id: str | None = None
    node_name: str | None = None
    new_daily_limit_usd: float | None = Field(None, ge=0.0)
    budget_mode: str | None = None
    allocations: list[BudgetAllocationInput] | None = None
    reason: str | None = None
    impact_summary: str | None = None
    cycle_date: str | None = None
    break_glass: bool = False
