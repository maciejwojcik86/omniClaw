## 1. Change And Planning Setup

- [x] 1.1 Author the M10a proposal, design, spec, and tasks artifacts for `m10a-agentic-workflow-verification-surface`, referencing the gap-analysis and implementation-plan docs.
- [x] 1.2 Update `docs/current-task.md` and `docs/plan.md` so M10a is the active change focused on final workflow confidence before moving to the next milestone.
- [x] 1.3 Update `docs/implement.md` with the immediate execution approach for the canonical verification-surface work.

## 2. Canonical Discovery And Reporting Surfaces

- [x] 2.1 Add the canonical active-agent catalog response with joined runtime/provider/budget metadata and tests for response shape/completeness.
- [x] 2.2 Add the canonical budget report response for organization-wide and per-node budget summaries, including comparison-friendly fields and tests.
- [x] 2.3 Add endpoint-backed helper wrappers for agent listing and budget report retrieval under `scripts/runtime/` and `scripts/budgets/`.

## 3. Canonical Invocation And Usage Surfaces

- [x] 3.1 Add a kernel-mediated prompt invocation surface for low-cost verification runs, including success and error-path tests.
- [x] 3.2 Add usage/session read endpoints for session summaries and node recent-session listings, including tests for token/cost/timing aggregation.
- [x] 3.3 Add endpoint-backed helper wrappers for prompt invocation and usage/session reporting under `scripts/runtime/` and `scripts/usage/`.

## 4. Canonical Workflow Packaging And Final Verification

- [x] 4.1 Classify verification scripts as canonical wrappers versus developer diagnostics and update documentation accordingly.
- [x] 4.2 Package the final budget-consumption verification SOP as a reusable skill under `.codex/skills/` and mirror/update it under `skills/` as required.
- [x] 4.3 Run the end-to-end verification workflow using only canonical endpoints/scripts, record results, and update `docs/documentation.md` with the validated runbook and any remaining gaps.
  - Validated on 2026-03-11 using only `list_agents.sh`, `get_budget_report.sh`, `invoke_agent_prompt.sh`, `get_session_summary.sh`, and `get_recent_sessions.sh`.
  - Verified agent discovery metadata, successful invocation, persisted usage summary, node recent-session listing, and post-run budget spend delta (`HR_Head_01 current_spend=0.08`, company `current_total_spend_usd=0.08`).

## 5. Validation And Closure

- [x] 5.1 Run targeted tests plus `uv run pytest -q`.
  - Targeted: `uv run pytest -q tests/test_usage_actions.py tests/test_runtime_actions.py tests/test_budgets_actions.py` (`22 passed`)
  - Full suite: `uv run pytest -q` (`87 passed`)
- [x] 5.2 Run `openspec validate --type change m10a-agentic-workflow-verification-surface --strict`.
- [x] 5.3 Complete the Skill Delta Review and update any related skills/scripts discovered during implementation.
  - Canonical verification SOP captured under `.codex/skills/verify-budget-consumption-workflow/` and mirrored to `skills/verify-budget-consumption-workflow/`.
