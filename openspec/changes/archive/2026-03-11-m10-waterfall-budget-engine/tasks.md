## 1. Change And Schema Setup

- [x] 1.1 Reconcile M10 change trackers and author the proposal, specs, design, and tasks artifacts for `m10-waterfall-budget-engine`.
- [x] 1.2 Extend the budget schema and Alembic migrations for budget modes, rollover reserve, manager review tracking, allocation rows, and cycle audit rows.
- [x] 1.3 Backfill deterministic defaults for existing budget rows and company config budgeting settings.

## 2. Waterfall Budget Engine

- [x] 2.1 Add repository support for company budget config reads, team allocation CRUD, cycle tracking, and subtree queries.
- [x] 2.2 Implement the waterfall calculation engine, daily cycle execution, subtree recalculation, and metered LiteLLM cap sync behavior.
- [x] 2.3 Extend `POST /v1/budgets/actions` with team view, allocation update, node mode update, cycle execution, and subtree recalculation actions.
- [x] 2.4 Emit direct-report budget change messages and downstream manager review markers after effective budget changes.

## 3. Runtime, Instructions, And Skills

- [x] 3.1 Add a budget maintenance loop to kernel lifespan startup and catch-up behavior after restart.
- [x] 3.2 Extend AGENTS placeholder rendering with budget awareness values and direct-team summaries.
- [x] 3.3 Generalize manager skill distribution and add the new `manage-team-budgets` master skill package plus developer SOP skill updates.

## 4. Verification, Docs, And Skill Capture

- [x] 4.1 Add and update tests covering schema migration, waterfall math, budget actions, instructions rendering, and notifications.
- [x] 4.2 Update `docs/current-task.md`, `docs/implement.md`, `docs/plan.md`, `docs/documentation.md`, and `AGENTS.md` repository map for M10.
- [x] 4.3 Run `uv run pytest -q` and `openspec validate --type change m10-waterfall-budget-engine --strict`, then complete the M10 Skill Delta Review.
