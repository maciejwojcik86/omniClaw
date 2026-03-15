---
name: manage-agent-budgets
description: Review manager/team budget state, update direct-report waterfall allocations, run daily budget cycles, and inspect budget-change notifications through OmniClaw kernel endpoints.
---

# Manage Agent Budgets

## Scope

Use this skill when you need to inspect team budgets, adjust direct-report allocations, change node budget mode, or manually trigger budget cycle operations for the M10 waterfall engine.

## Required Inputs

- running kernel API reachable at `${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}`
- local operators can start the stack with `uv run python main.py` (this also auto-starts the local LiteLLM proxy when `LITELLM_PROXY_URL` targets loopback)
- manager node name or ID for team-scoped actions
- optional JSON file containing allocation rows for `set_team_allocations`
- optional reason and impact summary text for budget-change notifications

## Execution Steps

1. View your own team budget:
   - `bash scripts/budgets/trigger_budget_action.sh --apply --action team_budget_view --actor-node-name <manager_name>`
2. Prepare allocation JSON for direct reports:
   - Example:
     ```json
     [
       {"child_node_name": "HR_Head_01", "percentage": 30.0},
       {"child_node_name": "Ops_Head_01", "percentage": 40.0}
     ]
     ```
   - Compatibility aliases also work: `agent_name` or `node_name` map to `child_node_name`; `node_id` maps to `child_node_id`; `share_percent` maps to `percentage`.
3. Apply direct-report allocation changes:
   - `bash scripts/budgets/trigger_budget_action.sh --apply --action set_team_allocations --actor-node-name <manager_name> --allocations-file <allocations.json> --reason "Quarterly rebalance" --impact-summary "More budget shifted to operations"`
   - If LiteLLM cap sync is unavailable, the allocation still applies and provider issues are returned under `sync_errors`.
4. Change a node between `metered` and `free` mode:
   - `bash scripts/budgets/trigger_budget_action.sh --apply --action set_node_budget_mode --actor-node-name <manager_name> --node-name <child_name> --budget-mode free`
5. Run or re-run the budget cycle:
   - `bash scripts/budgets/trigger_budget_action.sh --apply --action run_budget_cycle`
   - `bash scripts/budgets/trigger_budget_action.sh --apply --action run_budget_cycle --cycle-date 2026-03-08 --break-glass`
6. Capture the canonical org budget report:
   - `bash scripts/budgets/get_budget_report.sh --apply`
7. Check the recorded cost of a specific agent session canonically:
   - `bash scripts/usage/get_session_summary.sh --apply --session-key <session_key>`
8. Use direct DB inspection only for debugging:
   - `uv run python scripts/budgets/show_session_cost.py --agent-name <agent_name> --session-key <session_key>`

## Verification

- Confirm `team_budget_view` returns the manager row plus every direct report row.
- Confirm `set_team_allocations` returns a notification path for each changed direct report.
- Confirm provider-cap problems are reported under `sync_errors` instead of aborting the kernel-side allocation update.
- Confirm downstream managers show `review_required: true` after an upstream budget shift.
- Confirm metered nodes receive updated enforced caps and free nodes stay visible without provider cap warnings.
- Confirm the canonical budget report and session summary surfaces reflect the expected run.

## Fallback

- If the helper reports that the kernel is unreachable, start OmniClaw with `uv run python main.py` and rerun the budget action.
- If an allocation is rejected, re-check that every referenced child is a direct report and total percentages are `<= 100`.
- If provider sync fails, inspect LiteLLM connectivity separately and rerun `recalculate_subtree` or `run_budget_cycle`.
- If the team view looks stale, rerun `recalculate_subtree` and confirm the company budgeting config in `workspace/company_config.json`.
