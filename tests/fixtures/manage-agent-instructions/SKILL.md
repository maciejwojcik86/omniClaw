---
name: manage-agent-instructions
description: Kernel-backed workflow for reviewing and editing subordinate AGENTS templates outside deployed workspaces.
version: "1.0.0"
author: omniclaw-kernel
---

# Manage Agent Instructions

## Scope

Use this skill when you manage one or more subordinate agents and need to inspect, preview, update, or re-render their `AGENTS.md` instruction templates through the kernel.

## Required Inputs

- running kernel API reachable at `${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}`
- your manager node name or ID
- target subordinate node name or ID for template reads or updates
- optional local template draft file for `set_template`

## Supported Variables

Templates can include the following variables using `{{variable_name}}` syntax. The kernel will render these when the agent's instructions are synced.

- `{{node.name}}`: The name of the agent.
- `{{node.role_name}}`: The role assigned to the agent.
- `{{node.primary_model}}`: The primary model used by the agent (e.g., `openai-codex/gpt-5.4`).
- `{{current_time_utc}}`: The current time in UTC format.
- `{{manager.name}}`: The name of the agent's manager.
- `{{manager.id}}`: The ID of the agent's manager.
- `{{line_manager}}`: An alias for the name of the agent's manager.
- `{{subordinates_list}}`: A formatted list of the agent's direct subordinates.
- `{{inbox_unread_summary}}`: A summary of unread forms within the agent's inbox.

## Execution Steps

1. List manageable subordinates:
   - `bash skills/manage-agent-instructions/scripts/trigger_instructions_action.sh --apply --action list_accessible_targets --actor-node-name <manager_name>`
2. Read the current external template for one subordinate:
   - `bash skills/manage-agent-instructions/scripts/trigger_instructions_action.sh --apply --action get_template --actor-node-name <manager_name> --target-node-name <agent_name>`
3. Preview a revised template before saving it:
   - `bash skills/manage-agent-instructions/scripts/trigger_instructions_action.sh --apply --action preview_render --actor-node-name <manager_name> --target-node-name <agent_name> --template-file <draft_template.md>`
4. Save the revised template and force an immediate render:
   - `bash skills/manage-agent-instructions/scripts/trigger_instructions_action.sh --apply --action set_template --actor-node-name <manager_name> --target-node-name <agent_name> --template-file <draft_template.md>`
5. Re-render an existing template without editing it:
   - `bash skills/manage-agent-instructions/scripts/trigger_instructions_action.sh --apply --action sync_render --actor-node-name <manager_name> --target-node-name <agent_name>`

## Verification

- Confirm the template path returned by `get_template` lives under `workspace/nanobots_instructions/<agent_name>/AGENTS.md`.
- Confirm `preview_render` resolves placeholders such as `{{line_manager}}` and `{{inbox_unread_summary}}` without validation errors.
- Confirm the subordinate workspace `AGENTS.md` changes after `set_template` or `sync_render`.

## Fallback

- If `preview_render` rejects placeholders, remove unsupported `{{...}}` variables and retry with only the documented M08 placeholders.
- If authorization fails, confirm the target is in your current management chain and re-run `list_accessible_targets`.
- If the kernel endpoint is unavailable, inspect the template file directly under `workspace/nanobots_instructions/<agent_name>/AGENTS.md` and retry once the kernel is back up.
