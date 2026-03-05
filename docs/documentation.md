# OmniClaw Documentation

Living operator/developer documentation for current implementation.

## Delivery Status
- M00-M05: complete
- M06: complete and archived (`2026-03-05-m06-forms-ledger-state-machine`)
- Hardening change: complete and archived (`2026-03-05-hardening-runtime-ipc-core`)
- IPC invalid-feedback change: complete and archived (`2026-03-05-ipc-invalid-feedback-and-dedupe`)

## Runtime Basics
- Run tests: `uv run pytest -q`
- Start API: `uv run python main.py`
- Health: `GET /healthz`
- Default SQLite URL: `sqlite:///./workspace/omniclaw.db`
- Startup contract: database MUST be at Alembic head; run `uv run alembic upgrade head` before boot.
- IPC auto-scan while kernel is running:
  - enabled by default: `OMNICLAW_IPC_ROUTER_AUTO_SCAN_ENABLED=true`
  - interval seconds: `OMNICLAW_IPC_ROUTER_SCAN_INTERVAL_SECONDS` (default `5`)
- Runtime gateway host input is strictly validated (valid IP/hostname only).

## Core Endpoints
- `POST /v1/ipc/actions`
  - actions: `scan_forms` (primary), `scan_messages` (compatibility alias)
- `POST /v1/forms/actions`
  - `upsert_form_type`, `validate_form_type`, `activate_form_type`, `deprecate_form_type`, `delete_form_type`, `list_form_types`, `create_form`, `transition_form`, `acknowledge_message_read`

## Form-Centric Routing Model (M06)
- IPC routes markdown files from `outbox/pending` as **generic forms**.
- Required frontmatter (runtime):
  - `form_type`
  - `stage`
  - `decision`
  - optional `target` (for dynamic target stages)
- Legacy compatibility:
  - `type: MESSAGE` maps to `form_type: message`
  - `scan_messages` still accepted

Routing behavior:
- Kernel loads active form definition from `form_types`.
- Decision is validated against `workflow_graph.stages`.
- Kernel resolves next holder and routes file:
  - sender archive copy: `<sender>/outbox/archive/`
  - holder delivery copy: `<holder>/inbox/unread/` (when holder exists)
  - repo backup copy: `workspace/form_archive/<form_type>/<form_id>/`
- On undelivered validation/workflow failures:
  - source file is moved to sender `outbox/dead-letter/`
  - kernel writes a structured feedback artifact to recipient inbox (`target` first, sender fallback)
  - scan response includes `dead_letter_path` and `feedback_path`
- Forms ledger snapshot and append-only decision events are updated atomically per decision call.
- Form snapshots use optimistic lock versioning; stale transitions return conflict outcome.
- While kernel is running, background auto-scan periodically performs the same scan path as `POST /v1/ipc/actions` with `action=scan_forms` via non-blocking thread offload.

## Target Resolution
Supported stage targets:
- specific node id
- specific node name
- `{{initiator}}`
- `{{any}}` (requires frontmatter `target` / `target_node_id`)
- `{{var}}` (requires matching frontmatter field)
- `null`/`none` for terminal no-holder stages

## Skill Validation and Distribution
- Stage definitions include `required_skill`.
- Validation requires master skill file:
  - `workspace/forms/<form_type>/skills/<required_skill>/SKILL.md`
- During routing, kernel copies next-stage skill package to recipient workspaces under:
  - `<workspace>/skills/<required_skill>/`
- For `{{any}}` stages, distribution includes all active agent workspaces plus the resolved holder node.

## Workspace Canonical Artifacts
- `workspace/forms/<form_type>/workflow.json`
- `workspace/forms/<form_type>/skills/<required_skill>/...`
- `workspace/master_skills/form_workflow_authoring/SKILL.md`
- `workspace/form_archive/<form_type>/<form_id>/...`

Canonical shipped forms:
- `message`
- `deploy_new_agent`

## Tooling
- IPC trigger:
  - `scripts/ipc/trigger_ipc_action.sh --apply --action scan_forms`
- Dead-letter replay helper:
  - `scripts/ipc/requeue_dead_letter.sh --apply --workspace-root <workspace_root> --file <dead_letter_file>`
- Workspace-to-DB form sync (authoritative refresh):
  - `uv run scripts/forms/sync_form_types_from_workspace.py`
- Message acknowledge+archive helper (stage-skill tool):
  - `python workspace/forms/message/skills/read_and_acknowledge_internal_message/scripts/acknowledge_and_archive_message.py --apply --workspace-root <workspace_root> --form-file <form_file>`
- Forms action helper:
  - `scripts/forms/trigger_forms_action.sh`
- Publish workflow from workspace package:
  - `scripts/forms/upsert_workflow_from_workspace.sh --apply --activate --form-type <form_type>`
- Workflow smoke publisher:
  - `scripts/forms/smoke_form_workflows.sh [--apply]`

## Repo Structure (relevant)
- `src/omniclaw/forms/`: form type registry + decision engine
- `src/omniclaw/ipc/`: form IPC scanner/router
- `scripts/forms/`: form admin/publish/smoke scripts
- `scripts/ipc/`: ipc trigger + read/ack helper
- `workspace/forms/`: approved form workflow JSON packages
- `workspace/forms/<form_type>/skills/`: approved stage skill master copies per form type
- `workspace/master_skills/`: organization-level master skills
- `workspace/form_archive/`: routed-form backup trail

## Verification
- Current suite: `46 passed` on `uv run pytest -q`
