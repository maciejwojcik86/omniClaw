---
name: ipc-router-development
description: Developer SOP for OmniClaw generic form IPC routing (graph stages, holder handoff, skill distribution, and archive tracking).
license: MIT
compatibility: Python 3.11+, running OmniClaw kernel API
metadata:
  author: omniclaw
  version: "0.4"
---

Use this skill when implementing or extending form routing in `src/omniclaw/ipc/service.py`.

## Scope
- IPC action endpoint: `POST /v1/ipc/actions` (`scan_forms`, with `scan_messages` alias compatibility).
- Generic markdown form routing from sender `outbox/send`.
- Graph-driven decisions using active form definition from `form_types`.
- Filesystem lifecycle: sender archive, target inbox delivery, repo-level backup in `workspace/form_archive/`, and dead-letter + feedback handling for invalid forms.
- Next-stage skill distribution from `workspace/forms/<form_type>/skills/<required_skill>/...` to participant workspaces.
- Dispatched skills are normalized with `skill.json` beside `SKILL.md`; router writes missing required metadata keys (`name`, `version`, `description`, `author`).
- Kernel-managed routed metadata field `stage_skill` (next-stage required skill, empty string at terminal no-holder stages).
- Scan traversal is hard-bounded by action `limit` (router stops processing once scanned count reaches limit).
- Kernel auto-scan executes through non-blocking thread offload from lifespan loop.
- After a successful inbox delivery to an AGENT node, IPC can immediately wake that agent through runtime `invoke_prompt` using a company-workspace prompt template at `<company-workspace-root>/NEW_INBOX_MESSAGE_PROMPT.md`.

## Frontmatter Contract (runtime)
- `form_type`
- `stage`
- `decision`
- optional `target` for dynamic target stages (`{{any}}` / `{{var}}`) when an agent is queueing a form for scan
- optional `form_id` (required after first handoff)
- kernel-managed routed metadata, overwritten every hop:
  - `agent`: current stage holder after routing
  - `stage_skill`: current stage required skill
  - `target_agent`: decision-to-next-holder hint for the current routed stage

Notes:
- Routed forms no longer use `target` to mean “current holder”.
- On delivered `inbox/new` forms, `target` is cleared unless an agent later fills it for a dynamic route before re-queueing.

Legacy compatibility:
- `type: MESSAGE` maps to `form_type: message`.
- `scan_messages` action is accepted as an alias.

## Execution Steps
1. Create/queue form markdown in sender `outbox/send/`.
2. Trigger scan:
   - `./scripts/ipc/trigger_ipc_action.sh --apply --action scan_forms`
3. Verify filesystem results:
   - sender copy in `outbox/archive`
   - target copy in `inbox/new` (when next holder exists)
   - backup copy in `workspace/form_archive/<form_type>/<form_id>/`
   - routed frontmatter contains kernel-written `agent`, `stage_skill`, and `target_agent`
   - when the target is an AGENT and `NEW_INBOX_MESSAGE_PROMPT.md` exists, the IPC response item includes `wake_trigger.status=triggered`
4. Verify DB state:
   - `forms_ledger.current_status` updated to next stage
   - `forms_ledger.current_holder_node` updated to next holder (or null)
   - decision event appended in `form_transition_events`
5. Verify skill distribution:
   - next-stage skill copied to `<target_workspace>/skills/<required_skill>/`
   - dispatched skill contains `<target_workspace>/skills/<required_skill>/skill.json` with required metadata fields
   - terminal stage archive copy has `stage_skill: ""`
6. For undelivered files:
   - source file moved to `outbox/dead-letter`
   - kernel feedback artifact appears in recipient `inbox/new` (target-first, sender fallback)

## Verification Commands
- Dry-run scan:
  - `./scripts/ipc/trigger_ipc_action.sh --action scan_forms --limit 200`
- Apply scan:
  - `./scripts/ipc/trigger_ipc_action.sh --apply --action scan_forms`
- Requeue dead-letter file:
  - `./scripts/ipc/requeue_dead_letter.sh --apply --workspace-root <workspace> --file <name>.md`
- IPC tests:
  - `uv run pytest -q tests/test_ipc_actions.py`
- Deploy workflow live smoke runbook:
  - `scripts/forms/smoke_deploy_new_agent_e2e.sh [--apply]`

## Fallback
If a form is undelivered:
1. Read `failure_reason`, `dead_letter_path`, and `feedback_path` from IPC response.
2. Fix frontmatter or workflow/skill mismatch using feedback artifact fields.
3. Requeue explicitly from dead-letter using `scripts/ipc/requeue_dead_letter.sh`.
4. Rerun scan.
