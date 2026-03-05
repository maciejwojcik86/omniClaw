---
name: ipc-router-development
description: Developer SOP for OmniClaw generic form IPC routing (graph stages, holder handoff, skill distribution, and archive tracking).
license: MIT
compatibility: Python 3.11+, running OmniClaw kernel API
metadata:
  author: omniclaw
  version: "0.2"
---

Use this skill when implementing or extending form routing in `src/omniclaw/ipc/service.py`.

## Scope
- IPC action endpoint: `POST /v1/ipc/actions` (`scan_forms`, with `scan_messages` alias compatibility).
- Generic markdown form routing from sender `outbox/pending`.
- Graph-driven decisions using active form definition from `form_types`.
- Filesystem lifecycle: sender archive, target inbox delivery, repo-level backup in `workspace/form_archive/`, and dead-letter + feedback handling for invalid forms.
- Next-stage skill distribution from `workspace/forms/<form_type>/skills/<required_skill>/...` to participant workspaces.
- Scan traversal is hard-bounded by action `limit` (router stops processing once scanned count reaches limit).
- Kernel auto-scan executes through non-blocking thread offload from lifespan loop.

## Frontmatter Contract (runtime)
- `form_type`
- `stage`
- `decision`
- optional `target` for dynamic target stages (`{{any}}` / `{{var}}`)
- optional `form_id` (required after first handoff)

Legacy compatibility:
- `type: MESSAGE` maps to `form_type: message`.
- `scan_messages` action is accepted as an alias.

## Execution Steps
1. Create/queue form markdown in sender `outbox/pending/`.
2. Trigger scan:
   - `./scripts/ipc/trigger_ipc_action.sh --apply --action scan_forms`
3. Verify filesystem results:
   - sender copy in `outbox/archive`
   - target copy in `inbox/unread` (when next holder exists)
   - backup copy in `workspace/form_archive/<form_type>/<form_id>/`
4. Verify DB state:
   - `forms_ledger.current_status` updated to next stage
   - `forms_ledger.current_holder_node` updated to next holder (or null)
   - decision event appended in `form_transition_events`
5. Verify skill distribution:
   - next-stage skill copied to `<target_workspace>/skills/<required_skill>/`
6. For undelivered files:
   - source file moved to `outbox/dead-letter`
   - kernel feedback artifact appears in recipient `inbox/unread` (target-first, sender fallback)

## Verification Commands
- Dry-run scan:
  - `./scripts/ipc/trigger_ipc_action.sh --action scan_forms --limit 200`
- Apply scan:
  - `./scripts/ipc/trigger_ipc_action.sh --apply --action scan_forms`
- Requeue dead-letter file:
  - `./scripts/ipc/requeue_dead_letter.sh --apply --workspace-root <workspace> --file <name>.md`
- IPC tests:
  - `uv run pytest -q tests/test_ipc_actions.py`

## Fallback
If a form is undelivered:
1. Read `failure_reason`, `dead_letter_path`, and `feedback_path` from IPC response.
2. Fix frontmatter or workflow/skill mismatch using feedback artifact fields.
3. Requeue explicitly from dead-letter using `scripts/ipc/requeue_dead_letter.sh`.
4. Rerun scan.
