# OmniClaw Current Task

- active_change: `m10a-agentic-workflow-verification-surface`
- objective: Prove the current M10 budget implementation through canonical agent-usable discovery, invocation, usage-reporting, and budget-report workflow surfaces before moving to the next milestone.

## last_completed_change
- change: `m10-waterfall-budget-engine`
- archived_as: `openspec/changes/archive/2026-03-11-m10-waterfall-budget-engine`
- closure_notes:
  - Implemented the deterministic waterfall budget engine with company-pool funding, hierarchical allocations, daily cycle tracking, and reserve carry-forward.
  - Extended `POST /v1/budgets/actions` with team views, allocation updates, node mode changes, cycle execution, and subtree recalculation.
  - Added runtime budget maintenance, AGENTS budget placeholders, manager-budget skill distribution, and direct-report budget change notifications.
  - Validation completed before archive, including OpenSpec strict validation and pytest coverage for the M10 implementation.

## next_focus
- Active milestone extension: `m10a-agentic-workflow-verification-surface`
- Current execution: close the remaining canonical workflow gaps so budget verification can be run through supported endpoints/scripts rather than developer-only inspection paths.

## blockers
- None currently known for M10a implementation. The canonical verification path is now validated in the current environment.

## current_status
- `m10-waterfall-budget-engine` is archived.
- Supporting analysis docs are authored:
  - `docs/agentic-workflow-gap-analysis.md`
  - `docs/agentic-workflow-implementation-and-test-plan.md`
- M10a implementation is validated end-to-end:
  - canonical active-agent catalog with runtime/provider/budget metadata
  - canonical budget report action and wrapper
  - kernel-mediated prompt invocation surface and wrapper
  - usage/session read APIs and wrappers
  - canonical verification SOP skill mirrored between `.codex/skills/` and `skills/`
  - mock-mode canonical invocation now persists deterministic usage rows and budget spend for proof-path verification
- Validation completed:
  - `uv run pytest -q tests/test_usage_actions.py tests/test_runtime_actions.py tests/test_budgets_actions.py` (`22 passed`)
  - `uv run pytest -q` (`87 passed`)
  - `openspec validate --type change m10a-agentic-workflow-verification-surface --strict`
- Canonical wrapper-only end-to-end verification passed on 2026-03-11 using approved scripts only. Verified outputs included:
  - session summary for `cli:m10a-verify-20260311-1435`
  - recent-session listing for `HR_Head_01`
  - budget delta showing `HR_Head_01 current_spend=0.08` and company `current_total_spend_usd=0.08`

## next_up
- Keep `m10a-agentic-workflow-verification-surface` open for a follow-up hardening slice before archive.
- New follow-up task: internalize the currently customized Nanobot runtime into the OmniClaw monorepo and remove the current external-checkout coupling where `nanobot/agent/loop.py` directly imports `omniclaw.*` for usage logging.
- Target direction: preserve automatic runtime-level LLM usage logging, but move toward a cleaner OmniClaw-owned integration boundary suitable for future Nanobot customization without depending on a separately maintained external fork.
- Detailed next-session planning draft: `docs/nanobot-monorepo-internalization-openspec-plan.md`
