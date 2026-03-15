## Why

Routed forms currently overload `target` to mean the current holder after delivery. That is convenient for routing internals, but it is poor UX for agents and operators reading `inbox/new`: the header does not clearly separate who owns the current stage from who could receive the form next.

This change makes routed headers explicit. The kernel will expose the current holder as `agent` and a decision-to-next-holder hint as `target_agent`, while keeping `target` reserved for queue-time dynamic routing input.

## What Changes

- Add kernel-managed routed frontmatter field `agent`.
  - Value = current holder for the routed stage.
  - Terminal/no-holder stages write `agent: ""`.
- Add kernel-managed routed frontmatter field `target_agent`.
  - Value = readable decision-to-next-holder hint for the current routed stage.
  - `{{initiator}}` resolves to the actual initiator node name in the hint.
  - `{{any}}` remains explicit so the author knows they must choose a concrete target.
  - Terminal/no-holder-only stages write `target_agent: ""`.
- Keep `target` as an authoring-time input field for queued forms.
  - Delivered routed forms no longer use `target` to mean “current holder”.
  - Delivered routed forms clear `target` by default.
- Extend routed form frontmatter parsing/rendering to support multiline block values so `target_agent` can be readable.
- Update IPC tests, docs, and heartbeat/stage-skill guidance to the new contract.

## Impact

- `src/omniclaw/ipc/service.py`
- `tests/test_ipc_actions.py`
- `workspace/nanobot_workspace_templates/HEARTBEAT.md`
- `workspace/forms/deploy_new_agent/skills/*`
- `docs/*`
- `.codex/skills/ipc-router-development/SKILL.md`
