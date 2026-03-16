---
name: manage-team-budgets
description: Kernel-backed workflow for managers to inspect team budgets, update direct-report waterfall allocations, and understand budget change notices.
version: "1.0.0"
author: omniclaw-kernel
---

# Manage Team Budgets

## Scope

Use this skill when you manage one or more subordinate agents and need to review or rebalance the direct-report budget cascade owned by your node.

## Required Inputs

- running kernel API reachable at `${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}`
- local operators can start OmniClaw with `uv run omniclaw`; when the configured LiteLLM proxy URL is local, the proxy is started automatically too
- your manager node name or ID
- optional allocation JSON file for direct-report share updates
- short reason and expected impact text when changing allocations

## Execution Steps

1. Review your team budget:
   - `bash skills/manage-team-budgets/scripts/trigger_budget_action.sh --apply --action team_budget_view --actor-node-name <manager_name>`
2. Update direct-report shares with a JSON file:
   - `bash skills/manage-team-budgets/scripts/trigger_budget_action.sh --apply --action set_team_allocations --actor-node-name <manager_name> --allocations-file <allocations.json> --reason "<why>" --impact-summary "<impact>"`
   - Allocation rows should use `child_node_name` or `child_node_id` plus `percentage`.
   - Compatibility aliases also work: `agent_name`, `node_name`, `node_id`, and `share_percent`.
   - If provider-cap sync is unavailable, the allocation still applies and the response lists those issues under `sync_errors`.
3. Switch a direct report between `metered` and `free` mode:
   - `bash skills/manage-team-budgets/scripts/trigger_budget_action.sh --apply --action set_node_budget_mode --actor-node-name <manager_name> --node-name <child_name> --budget-mode <metered|free>`
4. If told by the kernel that your incoming pool changed, rerun step 1, adjust your allocations, and message your own direct reports.

## Verification

- Confirm the returned budget view includes you and every direct report.
- Confirm changed direct reports receive a budget update message in `inbox/new`.
- Confirm managers below you show review-required state after your rebalance until they reapply their team split.

## Fallback

- If the command says the kernel is unreachable, ask the operator to start OmniClaw with `uv run omniclaw`, then retry.
- If the kernel rejects the update, reduce total percentages so they do not exceed `100`.
- If your direct reports did not receive messages, check their `workspace_root` metadata and rerun the allocation update.
- If the budget view fails entirely, escalate to the operator with the error and stop manual edits.
