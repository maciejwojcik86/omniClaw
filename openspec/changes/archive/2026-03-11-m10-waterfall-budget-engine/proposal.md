## Why

OmniClaw currently treats budgets as flat per-node limits, which breaks the project’s top-down financial governance model and forces manual, error-prone allowance edits. M10 introduces a deterministic waterfall budget engine so company budget flows through the management tree, resets daily, carries forward unused reserves, and remains auditable.

## What Changes

- Add hierarchical budget allocation state driven by a company-level daily budget pool and manager-owned direct-report percentage splits.
- Add budget modes so metered nodes receive hard LiteLLM caps while free nodes remain outside spend enforcement but can still manage department reserve.
- Add a daily budget cycle that resets spend, rolls unused allowance into reserve, and recomputes subtree quotas deterministically.
- Extend budget actions with team views, manager allocation updates, node mode changes, and explicit budget-cycle execution/recalculation actions.
- Extend AGENT instruction rendering with live budget awareness placeholders and distribute a manager-facing team-budget skill to nodes with subordinates.
- Emit kernel-authored budget change messages to affected direct reports and mark downstream managers for required follow-up review.
- **BREAKING**: Direct per-node allowance edits are no longer authoritative for hierarchy-managed nodes and become break-glass only.

## Capabilities

### New Capabilities
- `waterfall-budget-engine`: Hierarchical company-pool allocation, daily reset/recalc, reserve carry-forward, and manager review propagation.

### Modified Capabilities
- `budget-management`: Expand from flat node allowance inspection/update into manager-scoped team views, direct-report allocation control, and strict quota recalculation.
- `litellm-integration`: Sync effective metered caps only for hierarchy-managed metered nodes while skipping free nodes.
- `agent-instructions-management`: Render additional budget-awareness placeholders and distribute the manager budget skill alongside instruction-management tooling.

## Impact

- Database schema: `budgets` table extensions plus new allocation/cycle tables.
- FastAPI budget API: new actions in `POST /v1/budgets/actions`.
- Runtime startup/lifespan: add a budget maintenance loop alongside IPC auto-scan.
- Instruction rendering: new placeholder context and expanded manager skill distribution.
- Workspace assets: new `workspace/master_skills/manage-team-budgets/` package and updated `workspace/company_config.json`.
