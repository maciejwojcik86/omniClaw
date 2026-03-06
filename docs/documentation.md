# OmniClaw Documentation

Living operator/developer documentation for current implementation.

## Delivery Status
- M00-M05: complete
- M06: complete and archived (`2026-03-05-m06-forms-ledger-state-machine`)
- Hardening change: complete and archived (`2026-03-05-hardening-runtime-ipc-core`)
- IPC invalid-feedback change: complete and archived (`2026-03-05-ipc-invalid-feedback-and-dedupe`)
- M07: complete (`m07-deploy-new-agent-e2e`)
- M07b: complete and archived (`2026-03-06-m07b-nanobot-runtime-migration`)

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
- Canonical runtime gateway template uses Nanobot with explicit workspace/config inputs:
  - `nanobot gateway --workspace {workspace_root} --config {config_path} --port {port}`

## Nanobot Provisioning Contract (M07b)
- AGENT directories default to `workspace/agents/<agent_name>/`.
- Canonical config path is `workspace/agents/<agent_name>/config.json`.
- Canonical workspace root is `workspace/agents/<agent_name>/workspace/`.
- `provision_agent` no longer creates a Linux user for AGENT nodes.
- `runtime_config_path` replaces `nullclaw_config_path` in canonical node metadata.
- Deployed workspaces include Nanobot context assets plus OmniClaw inbox/outbox folders.
- Canonical sample agents `Director_01`, `HR_Head_01`, and `Ops_Head_01` are reprovisioned under the repo-local Nanobot layout.

## Core Endpoints
- `POST /v1/ipc/actions`
  - actions: `scan_forms` (primary), `scan_messages` (compatibility alias)
- `POST /v1/forms/actions`
  - `upsert_form_type`, `validate_form_type`, `activate_form_type`, `deprecate_form_type`, `delete_form_type`, `list_form_types`, `create_form`, `transition_form`, `acknowledge_message_read`
- `POST /v1/forms/workspace/sync`
  - scans `workspace/forms/*/workflow.json`
  - validates graph targets and required skill master copies
  - upserts changed form definitions into DB (workflow graph remains stored in DB column)
  - optional activation and optional prune of missing DB-only definitions

## Form-Centric Routing Model (M06)
- IPC routes markdown files from `outbox/pending` as **generic forms**.
- Required frontmatter (runtime):
  - `form_type`
  - `stage`
  - `decision`
  - optional `target` (for dynamic target stages)
- Kernel-managed routed metadata (output-only, overwritten every hop):
  - `stage_skill` = next-stage `required_skill`
  - terminal/no-holder stage writes `stage_skill: ""`
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
- Workspace canonical form packages use hyphen-case stage skill names (for example `deploy-new-nanobot`).
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
- API-based workspace sync:
  - `curl -sS -X POST http://127.0.0.1:8000/v1/forms/workspace/sync -H 'content-type: application/json' -d '{"activate": true, "prune_missing": false}'`
- Message acknowledge+archive helper (stage-skill tool):
  - `python workspace/forms/message/skills/read-and-acknowledge-internal-message/scripts/acknowledge_and_archive_message.py --apply --workspace-root <workspace_root> --form-file <form_file>`
- Forms action helper:
  - `scripts/forms/trigger_forms_action.sh`
- Publish workflow from workspace package:
  - `scripts/forms/upsert_workflow_from_workspace.sh --apply --activate --form-type <form_type>`
- Workflow smoke publisher:
  - `scripts/forms/smoke_form_workflows.sh [--apply]`
- Deploy workflow E2E live smoke (preflight + sequential holder runbook):
  - `scripts/forms/smoke_deploy_new_agent_e2e.sh [--apply]`

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
- Targeted Nanobot migration slice: `20 passed` on `uv run pytest tests/test_schema_repository.py tests/test_runtime_actions.py tests/test_provisioning_actions.py -q`
- Full suite: `63 passed` on `uv run pytest -q`
- Live deploy smoke: `scripts/forms/smoke_deploy_new_agent_e2e.sh --apply --allow-agent-fallback --request-file 2026-03-06-m07b-nanobot-smoke-4.md`
- Manual reprovision retry: kernel `POST /v1/provisioning/actions` returned `200`, `Signal_Cartographer_01` was recreated under `workspace/agents/Signal_Cartographer_01/`, and a direct Nanobot `hello` smoke returned `Hello!`
