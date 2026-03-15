---
name: verify-budget-consumption-workflow
description: Run the canonical M10a verification workflow using only approved kernel endpoints and wrapper scripts to prove agent discovery, invocation, session usage, and budget delta visibility.
---

# Verify Budget Consumption Workflow

## Scope

Use this skill when you need to prove the current OmniClaw budget workflow end-to-end without relying on repo inspection, direct database reads, or non-canonical helper shortcuts.

This skill covers:
- active-agent discovery through the runtime catalog
- org budget snapshots before and after a test prompt
- low-cost prompt invocation through the kernel runtime endpoint
- canonical session and recent-session usage reads
- evidence capture using only approved endpoint-backed scripts

## Required Inputs

- running OmniClaw kernel at `${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}`
- one deployed target agent name or node id
- one low-cost verification prompt
- optional explicit session key for traceability

## Execution Steps

1. Start the local stack if needed:
   - `bash scripts/runtime/start_local_stack.sh`
2. Capture the active-agent catalog:
   - `bash scripts/runtime/list_agents.sh --apply`
3. Capture the pre-run budget report:
   - `bash scripts/budgets/get_budget_report.sh --apply`
4. Invoke a low-cost prompt against the target agent:
   - `bash scripts/runtime/invoke_agent_prompt.sh --apply --node-name <agent_name> --prompt "Reply with exactly: pong" --session-key <session_key>`
5. Read the canonical session summary:
   - `bash scripts/usage/get_session_summary.sh --apply --session-key <session_key>`
6. Read the target node recent sessions:
   - `bash scripts/usage/get_recent_sessions.sh --apply --node-id <node_id> --limit 5`
7. Capture the post-run budget report:
   - `bash scripts/budgets/get_budget_report.sh --apply`
8. Compare the before/after reports and confirm spend deltas on the expected node.

## Verification

- `list_agents.sh` returns the target node with runtime/budget metadata.
- `invoke_agent_prompt.sh` returns `action=invoke_prompt` and `invocation.status=completed`.
- `get_session_summary.sh` returns non-zero `llm_call_count` and a stable `session_key`.
- `get_recent_sessions.sh` includes the verification session in the node-scoped list.
- the second `get_budget_report.sh` shows spend movement consistent with the verification run.

## Fallback

- If the kernel is unreachable, start it with `uv run python main.py` or `bash scripts/runtime/start_local_stack.sh`.
- If prompt invocation fails, inspect the returned HTTP error body first; do not switch to direct repo inspection as the proof path.
- If usage or budget surfaces do not reflect the run, treat that as a product gap and capture it explicitly instead of compensating with privileged/manual fixes.
