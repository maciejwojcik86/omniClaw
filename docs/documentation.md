# OmniClaw Documentation

Living operator/developer documentation for current implementation.

## Delivery Status
- M00-M05: complete
- M06: complete and archived (`2026-03-05-m06-forms-ledger-state-machine`)
- Hardening change: complete and archived (`2026-03-05-hardening-runtime-ipc-core`)
- IPC invalid-feedback change: complete and archived (`2026-03-05-ipc-invalid-feedback-and-dedupe`)
- M07: complete (`m07-deploy-new-agent-e2e`)
- M07b: complete and archived (`2026-03-06-m07b-nanobot-runtime-migration`)
- M07c: complete (`m07c-routed-form-agent-hints`)
- M07d: complete and archived (`2026-03-07-m07d-template-and-inbox-path-rename`)
- M08: complete and archived (`2026-03-07-m08-context-injector`)
- M09: complete and archived (`2026-03-08-m09-litellm-key-management`)
- M09b: complete and archived (`2026-03-08-m09b-usage-and-session-tracking`)
- M10: complete (`m10-waterfall-budget-engine`)

## Runtime Basics
- Run tests: `PYTEST_ADDOPTS='-s' uv run pytest -q`
- Start API: `uv run python main.py`
- Local LiteLLM bootstrap: when `LITELLM_PROXY_URL` points at `localhost` or `127.0.0.1`, `main.py` auto-starts the local LiteLLM proxy and stops it on exit
- Stack wrapper: `bash scripts/runtime/start_local_stack.sh`
- Health: `GET /healthz`
- Default SQLite URL: `sqlite:///./workspace/omniclaw.db`
- Startup contract: database MUST be at Alembic head; run `uv run alembic upgrade head` before boot.
- IPC auto-scan while kernel is running:
  - enabled by default: `OMNICLAW_IPC_ROUTER_AUTO_SCAN_ENABLED=true`
  - interval seconds: `OMNICLAW_IPC_ROUTER_SCAN_INTERVAL_SECONDS` (default `5`)
- Budget auto-cycle while kernel is running:
  - enabled by default: `OMNICLAW_BUDGET_AUTO_CYCLE_ENABLED=true`
  - poll interval seconds: `OMNICLAW_BUDGET_AUTO_CYCLE_POLL_INTERVAL_SECONDS` (default `60`)
- Runtime gateway host input is strictly validated (valid IP/hostname only).
- Canonical runtime gateway template uses Nanobot with explicit workspace/config inputs:
  - `nanobot gateway --workspace {workspace_root} --config {config_path} --port {port}`
- Default company config path: `workspace/company_config.json`

## Nanobot Provisioning Contract (M07b)
- AGENT directories default to `workspace/agents/<agent_name>/`.
- Canonical config path is `workspace/agents/<agent_name>/config.json`.
- Canonical workspace root is `workspace/agents/<agent_name>/workspace/`.
- Canonical baseline template root is `workspace/nanobot_workspace_templates/`.
- `provision_agent` no longer creates a Linux user for AGENT nodes.
- `runtime_config_path` replaces `nullclaw_config_path` in canonical node metadata.
- Deployed workspaces include Nanobot context assets plus OmniClaw inbox/outbox folders.
- Canonical sample agents `Director_01`, `HR_Head_01`, and `Ops_Head_01` are reprovisioned under the repo-local Nanobot layout.

## Waterfall Budget Engine (M09 / M10)
- Budgeting is company-pool driven from `workspace/company_config.json`:
  - `budgeting.daily_company_budget_usd`
  - `budgeting.root_allocator_node`
  - `budgeting.reset_time_utc`
- Canonical budget state lives in the database:
  - `budgets` stores spend, fresh inflow, effective cap, budget mode, rollover reserve, and manager review markers.
  - `budget_allocations` stores manager -> direct-report percentage shares.
  - `budget_cycles` stores the per-UTC-day reset/recalculation audit trail.
- Budget modes:
  - `metered`: enforced provider cap synced to LiteLLM.
  - `free`: visible in reporting and reserve math, but skipped during provider cap sync.
- The configured root allocator is forced into `free` mode during waterfall recomputation.
- Daily cycle behavior:
  - resets `current_spend`
  - carries unused prior controlled budget into `rollover_reserve_usd`
  - recalculates fresh inflow from the current hierarchy/allocation tree
  - records one `budget_cycles` row per UTC day and catches up safely after restart
- `set_team_allocations` writes kernel-authored budget update messages into affected direct reports' `inbox/new` directories and marks downstream managers with `review_required_at`.
- `set_team_allocations` accepts canonical allocation keys (`child_node_name` / `child_node_id` + `percentage`) and compatibility aliases (`agent_name`, `node_name`, `node_id`, `share_percent`).
- When LiteLLM cap sync fails, kernel-side budget recalculation still succeeds and reports provider issues under `sync_errors`.

## Core Endpoints
- `POST /v1/ipc/actions`
  - actions: `scan_forms` (primary), `scan_messages` (compatibility alias)
- `POST /v1/instructions/actions`
  - `list_accessible_targets`, `get_template`, `preview_render`, `set_template`, `sync_render`
- `POST /v1/forms/actions`
  - `upsert_form_type`, `validate_form_type`, `activate_form_type`, `deprecate_form_type`, `delete_form_type`, `list_form_types`, `create_form`, `transition_form`, `acknowledge_message_read`
- `POST /v1/forms/workspace/sync`
  - scans `workspace/forms/*/workflow.json`
  - validates graph targets and required skill master copies
  - upserts changed form definitions into DB (workflow graph remains stored in DB column)
  - optional activation and optional prune of missing DB-only definitions
- `POST /v1/budgets/actions`
  - `sync_all_costs`, `sync_node_cost`, `update_node_allowance`
  - `team_budget_view`, `set_team_allocations`, `set_node_budget_mode`
  - `run_budget_cycle`, `recalculate_subtree`, `budget_report`
- `POST /v1/runtime/actions`
  - `gateway_start`, `gateway_stop`, `gateway_status`, `list_agents`, `invoke_prompt`
  - `invoke_prompt` runs a kernel-mediated low-cost Nanobot CLI prompt against one deployed agent using explicit workspace/config inputs and returns canonical reply/metadata payloads.
- `GET /v1/usage/sessions/{session_key}/summary`
  - returns canonical aggregated call count, tokens, cost, timing span, and provider/model breakdown for one session key.
- `GET /v1/usage/nodes/{node_id}/recent-sessions`
  - returns recent per-session usage summaries grouped by node.
- `POST /v1/sessions/export`
  - exports native Nanobot `SessionManager` JSONL transcripts to a target directory and records metadata via `usage` namespace.

## Form-Centric Routing Model (M06 / M07c)
- IPC routes markdown files from `outbox/send` as **generic forms**.
- Required frontmatter (runtime):
  - `form_type`
  - `stage`
  - `decision`
  - optional `target` (only when a queued form must choose a dynamic next holder such as `{{any}}` / `{{var}}`)
- Kernel-managed routed metadata (output-only, overwritten every hop):
  - `agent` = current routed stage holder
  - `stage_skill` = current routed stage `required_skill`
  - `target_agent` = decision-to-next-holder hint for the current routed stage
  - terminal/no-holder stage writes `stage_skill: ""`, `agent: ""`, and `target_agent: ""`
- Legacy compatibility:
  - `type: MESSAGE` maps to `form_type: message`
  - `scan_messages` still accepted

Routing behavior:
- Kernel loads active form definition from `form_types`.
- Decision is validated against `workflow_graph.stages`.
- Kernel resolves next holder and routes file:
  - sender archive copy: `<sender>/outbox/archive/`
  - holder delivery copy: `<holder>/inbox/new/` (when holder exists)
  - repo backup copy: `workspace/form_archive/<form_type>/<form_id>/`
- On undelivered validation/workflow failures:
  - source file is moved to sender `outbox/dead-letter/`
  - kernel writes a structured feedback artifact to recipient inbox (`target` first, sender fallback)
  - scan response includes `dead_letter_path` and `feedback_path`
- Forms ledger snapshot and append-only decision events are updated atomically per decision call.
- Form snapshots use optimistic lock versioning; stale transitions return conflict outcome.
- While kernel is running, background auto-scan periodically performs the same scan path as `POST /v1/ipc/actions` with `action=scan_forms` via non-blocking thread offload.

Delivered form semantics:
- `agent` tells the reader which node is currently responsible for the routed stage.
- `target_agent` is guidance only; it lists which next holder each allowed decision will resolve to.
- Delivered forms no longer use `target` to mean “current holder”.
- Agents should only populate `target` before queueing when the chosen decision leads to a dynamic target stage.

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
- `workspace/master_skills/manage-team-budgets/`
- `workspace/form_archive/<form_type>/<form_id>/...`
- `workspace/company_config.json`
- `workspace/nanobot_workspace_templates/`
- `workspace/nanobots_instructions/<node_name>/AGENTS.md`

Canonical shipped forms:
- `message`
- `deploy_new_agent`

## Instruction Rendering And Manager Skills
- AGENTS rendering supports the original node/manager/inbox placeholders plus:
  - `{{budget.mode}}`
  - `{{budget.daily_inflow_usd}}`
  - `{{budget.rollover_reserve_usd}}`
  - `{{budget.remaining_usd}}`
  - `{{budget.review_required_notice}}`
  - `{{budget.direct_team_summary}}`
- Managers with subordinates receive these organization-level master skills in their workspace `skills/` directory:
  - `manage-agent-instructions`
  - `manage-team-budgets`

## Tooling
- Local stack launcher:
  - `scripts/runtime/start_local_stack.sh`
- Agent CLI wrapper with correct `PYTHONPATH` for usage logging:
  - `scripts/runtime/run_agent.sh --agent-name <agent_name> --message <text> [--session-key <key>]`
- Budget action helper:
  - `scripts/budgets/trigger_budget_action.sh`
  - HTTP 4xx responses print the kernel response body for faster operator debugging
- Session cost summary helper:
  - `uv run python scripts/budgets/show_session_cost.py --agent-name <agent_name> --session-key <key>`
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
- `src/omniclaw/budgets/`: waterfall budget engine, budget actions/service, and LiteLLM cap reconciliation
- `src/omniclaw/forms/`: form type registry + decision engine
- `src/omniclaw/instructions/`: AGENTS template management, rendering, and manager skill distribution
- `src/omniclaw/ipc/`: form IPC scanner/router
- `src/omniclaw/usage/`: LLM usage logging and session export services
- `scripts/budgets/`: budget action helpers
- `scripts/forms/`: form admin/publish/smoke scripts
- `scripts/ipc/`: ipc trigger + read/ack helper
- `workspace/company_config.json`: company-level instruction and budgeting config
- `workspace/forms/`: approved form workflow JSON packages
- `workspace/forms/<form_type>/skills/`: approved stage skill master copies per form type
- `workspace/master_skills/`: organization-level master skills
- `workspace/nanobot_workspace_templates/`: canonical deployed Nanobot workspace template source
- `workspace/nanobots_instructions/`: external instruction template roots per node
- `workspace/form_archive/`: routed-form backup trail

## Canonical M10a budget-consumption verification runbook
1. Start the kernel stack: `bash scripts/runtime/start_local_stack.sh`
2. Capture the current active-agent catalog: `bash scripts/runtime/list_agents.sh --apply`
3. Capture the current org budget report: `bash scripts/budgets/get_budget_report.sh --apply`
4. Invoke one low-cost verification prompt against the target agent:
   - `bash scripts/runtime/invoke_agent_prompt.sh --apply --node-name <agent_name> --prompt "Reply with exactly: pong" --session-key cli:m10a-verify`
5. Read the canonical session summary:
   - `bash scripts/usage/get_session_summary.sh --apply --session-key cli:m10a-verify`
6. Read the node recent-session list:
   - `bash scripts/usage/get_recent_sessions.sh --apply --node-id <node_id> --limit 5`
7. Re-run the budget report and compare spend deltas:
   - `bash scripts/budgets/get_budget_report.sh --apply`
8. Only use the diagnostic scripts when debugging product gaps; they do not count as completion evidence for this runbook.

Validated evidence from 2026-03-11:
- target agent: `HR_Head_01` (`74031f33-c72d-4f0a-8b47-2ee770062b12`)
- verification session: `cli:m10a-verify-20260311-1435`
- session summary showed `llm_call_count=1`, `total_tokens=8`, `cost_usd=0.08`
- recent-session listing for `HR_Head_01` included the verification session
- post-run budget report showed `HR_Head_01 current_spend=0.08`, `remaining_budget_usd=2.62`, and company `current_total_spend_usd=0.08`

## Verification
- Targeted Nanobot migration slice: `20 passed` on `uv run pytest tests/test_schema_repository.py tests/test_runtime_actions.py tests/test_provisioning_actions.py -q`
- Full suite: `74 passed` on `PYTEST_ADDOPTS='-s' uv run pytest -q`
- Template/inbox rename slice: `30 passed` on `uv run pytest -q tests/test_nanobot_skill_wrappers.py tests/test_ipc_actions.py tests/test_schema_repository.py`
- Strict change validation: `openspec validate --type change m10-waterfall-budget-engine --strict`
- Strict change validation: `openspec validate --type change m07d-template-and-inbox-path-rename --strict`
- Live deploy smoke: `scripts/forms/smoke_deploy_new_agent_e2e.sh --apply --allow-agent-fallback --request-file 2026-03-06-m07b-nanobot-smoke-4.md`
- Manual reprovision retry: kernel `POST /v1/provisioning/actions` returned `200`, `Signal_Cartographer_01` was recreated under `workspace/agents/Signal_Cartographer_01/`, and a direct Nanobot `hello` smoke returned `Hello!`
