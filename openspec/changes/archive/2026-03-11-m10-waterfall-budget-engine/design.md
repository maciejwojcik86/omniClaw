## Context

M09 added LiteLLM virtual keys and flat node allowance updates, but the runtime still treats budgets as independent per-node caps. The PRD and milestone plan require top-down financial governance: a company pool controlled at the top, direct-report allocations per manager, daily reset/recalculation, and deterministic visibility in both APIs and rendered AGENTS instructions. The current code already has hierarchy metadata, budget rows, LiteLLM sync paths, instruction rendering, and a FastAPI lifespan loop for IPC autoscan, so M10 should extend those mechanisms rather than introduce a second orchestration path.

## Goals / Non-Goals

**Goals:**
- Add canonical schema for budget mode, rollover reserve, allocation percentages, and auditable budget cycles.
- Compute strict waterfall budgets from company config through the existing hierarchy graph.
- Expose manager-scoped budget operations through the existing `/v1/budgets/actions` route.
- Run a daily budget cycle automatically and catch up after restart.
- Surface budget context inside AGENTS templates and distribute a manager team-budget skill.
- Notify affected direct reports and mark downstream managers for follow-up review.

**Non-Goals:**
- Budget request forms or approval workflows.
- Cross-charge or reserve clawback between teams.
- Subscription-soft-limit behavior or additional budget modes beyond `metered` and `free`.
- Per-call usage instrumentation work from the stray `m09b` change.

## Decisions

### 1. Store company pool in `workspace/company_config.json`
- **Decision**: Add a `budgeting` section in company config containing `daily_company_budget_usd`, `root_allocator_node`, and `reset_time_utc`.
- **Rationale**: The user explicitly chose a global pool outside any node record. This keeps company funding configuration operator-controlled while node-level computed state remains in the DB.
- **Rejected alternative**: Store the company pool on the top director's budget row. Rejected because the top director is intentionally outside spend dependence and should not double as both consumer and funding source.

### 2. Persist direct-report shares in a new `budget_allocations` table
- **Decision**: Model manager -> child percentage shares separately from computed budget state.
- **Rationale**: The waterfall engine needs durable saved shares so subtree budgets can be recomputed immediately after any upstream change without waiting for manual manager input.
- **Rejected alternative**: Reuse `budgets.allocated_percentage`. Rejected because that field cannot model multiple direct reports per manager safely and conflates desired allocation intent with computed result.

### 3. Keep computed budget state on `budgets`
- **Decision**: Extend `budgets` with `budget_mode`, `rollover_reserve_usd`, and `review_required_at`, and reinterpret `current_daily_allowance` as the node's fresh daily inflow before reserve.
- **Rationale**: `budgets` already holds node-centric runtime budget state. Keeping computed inflow/spend/reserve together minimizes query complexity for rendering and API responses.
- **Rejected alternative**: Move all computed state into a separate table. Rejected because every caller already loads `budgets` by node and the extra join would not buy meaningful separation.

### 4. Recompute entire affected subtrees using saved shares
- **Decision**: On cycle runs or parent allocation changes, recursively recompute every affected subtree from the most recently saved child shares. Nodes with children keep any unallocated remainder as department reserve.
- **Rationale**: This satisfies strict quota enforcement immediately while still letting downstream managers review and reapply their team split after a change notice.
- **Rejected alternative**: Pause descendants until downstream managers manually confirm. Rejected because it interrupts work and violates the desire for automatic cascade behavior.

### 5. Treat `free` nodes as visible but unenforced
- **Decision**: Free nodes participate in reporting and can retain reserve, but provider cap sync skips them.
- **Rationale**: The user wants directors/local-model agents outside hard spend dependence while still allowing them to manage department budgets.
- **Rejected alternative**: Remove free nodes from the tree entirely. Rejected because they still sit in the management hierarchy and need reporting/notification context.

### 6. Keep notifications as kernel-authored inbox messages
- **Decision**: Write deterministic MESSAGE markdown files directly into affected recipients' `inbox/new` directories.
- **Rationale**: The kernel already writes structured feedback messages into inboxes without round-tripping through agent outboxes. The same pattern is sufficient for budget notices and avoids coupling M10 to a new form flow.
- **Rejected alternative**: Create a new budget form workflow. Rejected because formal budget request/approval is explicitly out of scope for M10.

### 7. Generalize manager skill distribution with an allowlist
- **Decision**: Extend instruction service distribution from one hardcoded manager skill to a small allowlist of organization-level manager skills: `manage-agent-instructions` and `manage-team-budgets`.
- **Rationale**: M10 needs an additional manager-only skill and the existing distribution logic is already the right integration point.
- **Rejected alternative**: Distribute all `workspace/master_skills/*` packages to every manager. Rejected because not every master skill is intended for automatic organization-wide manager distribution.

## Risks / Trade-offs

- **[Config / DB drift]** → Mitigation: treat company config as the root funding input and write all computed outcomes plus budget cycle records into the DB for auditability.
- **[Quota mismatch between DB and LiteLLM]** → Mitigation: route all metered cap writes through one budget engine path and keep sync/recalc actions idempotent.
- **[Recursive recalculation bugs]** → Mitigation: keep allocation math in a dedicated engine with focused repository tests covering remainder, reserve carry-forward, and subtree updates.
- **[Notification spam during repeated adjustments]** → Mitigation: notify direct reports only and include a concise reason/impact summary per recalculation request.
- **[Dirty repo / partial user changes]** → Mitigation: scope edits narrowly to budget, instructions, runtime, skill, and tracker files without reverting unrelated worktree changes.

## Migration Plan

1. Add Alembic migration to extend `budgets` and create `budget_allocations` and `budget_cycles`.
2. Backfill existing budget rows with deterministic defaults: `metered` mode, zero reserve, no review flag.
3. Backfill `budgets.parent_node_id` from the existing hierarchy when available so legacy rows align with the waterfall tree.
4. Update company config to include the `budgeting` section and preserve existing `instructions.access_scope`.
5. Deploy application changes, run the new budget cycle once, and confirm metered node caps reconcile.

**Rollback**
- Downgrade the migration to remove new columns/tables.
- Revert the company config `budgeting` section if needed.
- Resume flat allowance usage through the pre-M10 budget API.

## Open Questions

- None for M10. Subscription-soft-limit behavior and reserve clawback are explicitly deferred.
