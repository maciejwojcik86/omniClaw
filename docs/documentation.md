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
- M10a: complete and archived (`2026-03-15-m10a-agentic-workflow-verification-surface`)
- M11: complete and archived (`2026-03-15-m11-master-skill-lifecycle`)
- M11b: complete and archived (`2026-03-15-m11b-configurable-company-workspaces`)
- M12: complete and archived (`2026-03-16-m12-nanobot-monorepo-internalization`)
- M12b: complete and archived (`2026-03-16-m12b-global-company-registry`)

## Runtime Basics
- Run tests: `uv run pytest -q tests`
- Start API: `uv run omniclaw --company <slug-or-display-name> [--global-config-path <path>] [--database-url <url>]`
- Local LiteLLM bootstrap: when `LITELLM_PROXY_URL` points at `localhost` or `127.0.0.1`, `omniclaw` auto-starts the local LiteLLM proxy and stops it on exit
- Stack wrapper: `bash scripts/runtime/start_local_stack.sh --company <slug-or-display-name> [--global-config-path <path>] [--database-url <url>]`
- Health: `GET /healthz`
- Global OmniClaw registry: `<user-home>/.omniClaw/config.json`
- Default SQLite URL: `sqlite:///<company-workspace-root>/omniclaw.db`
- Startup contract: database MUST be at Alembic head; run `uv run alembic upgrade head` before boot.
- IPC auto-scan while kernel is running:
  - enabled by default: `OMNICLAW_IPC_ROUTER_AUTO_SCAN_ENABLED=true`
  - interval seconds: `OMNICLAW_IPC_ROUTER_SCAN_INTERVAL_SECONDS` (default `5`)
- Budget auto-cycle while kernel is running:
  - enabled by default: `OMNICLAW_BUDGET_AUTO_CYCLE_ENABLED=true`
  - poll interval seconds: `OMNICLAW_BUDGET_AUTO_CYCLE_POLL_INTERVAL_SECONDS` (default `60`)
- Runtime gateway host input is strictly validated (valid IP/hostname only).
- Runtime binary selection defaults to `nanobot` and can be overridden with `OMNICLAW_RUNTIME_COMMAND_BIN`.
- Canonical runtime gateway template uses Nanobot with explicit workspace/config inputs:
  - `{runtime_bin} gateway --workspace {workspace_root} --config {config_path} --port {port}`
- Canonical company settings source: `~/.omniClaw/config.json -> companies.<slug>`
- Legacy fallback: raw workspace/config overrides remain available for tests and migration tooling, but they are no longer the documented operator path.

## Nanobot Monorepo Internalization (M12)
- The customized Nanobot runtime now lives inside this repo at `third_party/nanobot/`.
- Root dependency resolution now installs `nanobot-ai` from that vendored path instead of from `/home/macos/nanobot`.
- OmniClaw is installable as a package with the `omniclaw` CLI entrypoint.
- `main.py` and `python -m omniclaw` remain compatibility shims, but `omniclaw` is the canonical kernel CLI.
- Canonical repo bootstrap is `bash scripts/install/bootstrap_monorepo.sh`, which syncs a shared environment containing both `omniclaw` and `nanobot`.
- The canonical OmniClaw monorepo test boundary is `uv run pytest -q tests`; vendored Nanobot upstream tests remain opt-in fork-maintenance work from `third_party/nanobot/`.
- OmniClaw-managed runtime launches pass explicit env vars to Nanobot for:
  - canonical database URL
  - node ID and node name
  - runtime output root
  - runtime prompt-log root
- Vendored Nanobot providers now write final request-body prompt artifacts under `<agent-workspace>/drafts/runtime/prompt_logs/` for OmniClaw-managed calls only.
- Prompt log artifacts include provider/model/session metadata and final provider request bodies, but exclude API keys and auth headers.
- Validation evidence:
  - `bash scripts/install/bootstrap_monorepo.sh`
  - `uv run omniclaw --help`
  - `uv run nanobot --help`
  - `uv run python -m omniclaw --help`
  - `openspec validate --type change m12-nanobot-monorepo-internalization --strict`
  - `uv run pytest -q tests` (`101 passed in 219.16s`)

## Global Company Registry (M12b)
- OmniClaw now keeps company configuration in one host-level registry file: `~/.omniClaw/config.json`.
- `companies` is a dict keyed by stable company slug.
- Each company entry stores:
  - `display_name`
  - `workspace_root`
  - `instructions`
  - `budgeting`
  - `hierarchy`
  - `skills`
  - `models`
  - `runtime`
- The selected company workspace still owns editable/runtime assets:
  - `omniclaw.db`
  - `agents/`
  - `forms/`
  - `master_skills/`
  - `nanobots_instructions/`
  - `nanobot_workspace_templates/`
  - `form_archive/`
  - `logs/`
  - `retired/`
  - `runtime_packages/`
  - `finances/`
- Missing workspace roots referenced by the global registry now fail fast during startup.
- Repo `workspace/` remains the seed/migration input used by bootstrap tooling, fixtures, and tests.
- Current local developer migration has been applied to `/home/macos/.omniClaw/workspace`, with company settings now stored in `/home/macos/.omniClaw/config.json`.
- Validation evidence:
  - `openspec validate --type change m12b-global-company-registry --strict`
  - `PYTEST_ADDOPTS='-s' uv run pytest -q tests` (`101 passed in 185.58s`)
  - `env OMNICLAW_LITELLM_AUTO_START_LOCAL_PROXY=false timeout 10s uv run omniclaw --company omniclaw --host 127.0.0.1 --port 8012` (startup completed; timeout intentionally stopped the server)

## Nanobot Provisioning Contract (M07b)
- AGENT directories default to `<company-workspace-root>/agents/<agent_name>/`.
- Canonical config path is `<company-workspace-root>/agents/<agent_name>/config.json`.
- Canonical workspace root is `<company-workspace-root>/agents/<agent_name>/workspace/`.
- Canonical baseline template root is `<company-workspace-root>/nanobot_workspace_templates/`.
- `provision_agent` no longer creates a Linux user for AGENT nodes.
- `runtime_config_path` replaces `nullclaw_config_path` in canonical node metadata.
- Deployed workspaces include Nanobot context assets plus OmniClaw inbox/outbox folders.
- Canonical sample agents `Director_01`, `HR_Head_01`, and `Ops_Head_01` now resolve under the selected company workspace root.

## Master Skill Lifecycle (M11)
- OmniClaw now treats every skill visible inside an agent workspace `skills/` directory as a kernel-controlled master skill.
- Source packages stay in place:
  - loose company skills: `<company-workspace-root>/master_skills/<skill_name>/`
  - form-linked stage skills: `<company-workspace-root>/forms/<form_type>/skills/<skill_name>/`
- Loose companion skills that mirror a workflow stage must use a distinct name because `master_skills.name` is globally unique across both loose and form-linked entries.
- Example: `<company-workspace-root>/master_skills/deploy-new-nanobot-standalone/` is the manually assignable companion of the workflow-owned `<company-workspace-root>/forms/deploy_new_agent/skills/deploy-new-nanobot/`.
- The shared catalog lives in `master_skills`:
  - `master_path` stores the canonical source directory
  - `form_type_key` is `null` for loose company skills and set for form-linked skills
  - `lifecycle_status` (`DRAFT`, `ACTIVE`, `DEACTIVATED`) controls loose-skill assignment eligibility
  - `validation_status` remains as compatibility metadata
- Effective workspace delivery lives in `node_skill_assignments` with sources:
  - `MANUAL`
  - `DEFAULT`
  - `FORM_STAGE`
- `POST /v1/skills/actions` and `src/omniclaw/skills/` own catalog mutation, assignment mutation, and filesystem reconciliation.
- `sync_agent_skills` wipes and rebuilds only the agent workspace `skills/` directory from DB-approved assignments, leaving repo-root `.codex/skills/`, `skills/`, and `.agents/` untouched.
- `~/.omniClaw/config.json -> companies.<slug>.skills.default_agent_skill_names` controls company defaults; `provision_agent` seeds those defaults before the initial workspace sync.
- Manager policy skills (`manage-agent-instructions`, `manage-team-budgets`) are now ordinary loose master skills assigned through `DEFAULT` rows instead of hardcoded file-copy logic.
- Form activation/workspace sync writes `FORM_STAGE` assignments, and IPC routing re-syncs affected target agents so approved stage skills are restored after any local drift.

## Waterfall Budget Engine (M09 / M10)
- Budgeting is company-pool driven from `~/.omniClaw/config.json -> companies.<slug>.budgeting`:
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
  - scans `<company-workspace-root>/forms/*/workflow.json`
  - validates graph targets and required skill master copies
  - upserts changed form definitions into DB (workflow graph remains stored in DB column)
  - optional activation and optional prune of missing DB-only definitions
- `POST /v1/skills/actions`
  - `list_master_skills`, `list_active_master_skills`
  - `draft_master_skill`, `update_master_skill`, `set_master_skill_status`
  - `list_agent_skill_assignments`, `assign_master_skills`, `remove_master_skills`, `sync_agent_skills`
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
  - company archive copy: `<company-workspace-root>/form_archive/<form_type>/<form_id>/`
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
  - `<company-workspace-root>/forms/<form_type>/skills/<required_skill>/SKILL.md`
- Workspace canonical form packages use hyphen-case stage skill names (for example `deploy-new-nanobot`).
- Form workspace sync and activation catalog these packages into the shared `master_skills` table without moving them out of the workflow package.
- Activation and routing write `FORM_STAGE` assignment rows for the currently eligible target agents.
- Agent workspaces receive approved stage skills through the shared reconciliation path:
  - `<workspace>/skills/<required_skill>/`
- For `{{any}}` stages, assignment refresh includes all active agent workspaces plus the resolved holder when one is known.

## Company Workspace Canonical Artifacts
- `<company-workspace-root>/forms/<form_type>/workflow.json`
- `<company-workspace-root>/forms/<form_type>/skills/<required_skill>/...`
- `<company-workspace-root>/master_skills/form_workflow_authoring/SKILL.md`
- `<company-workspace-root>/master_skills/deploy-new-nanobot-standalone/`
- `<company-workspace-root>/master_skills/manage-team-budgets/`
- `<company-workspace-root>/form_archive/<form_type>/<form_id>/...`
- `<company-workspace-root>/nanobot_workspace_templates/`
- `<company-workspace-root>/nanobots_instructions/<node_name>/AGENTS.md`
- `<company-workspace-root>/retired/forms/`
- `<company-workspace-root>/retired/master_skills/`
- `~/.omniClaw/config.json`

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
- `sync_render` for `all_active_agents` now delegates skill reconciliation to the shared skills service after rendering AGENTS files.
- Managers with subordinates receive these organization-level master skills through assignment-based reconciliation in their AGENT workspace `skills/` directory:
  - `manage-agent-instructions`
  - `manage-team-budgets`

## Tooling
- Local stack launcher:
  - `scripts/runtime/start_local_stack.sh --company <slug-or-display-name>`
- Agent CLI wrapper with OmniClaw runtime integration env:
  - `scripts/runtime/run_agent.sh --company <slug-or-display-name> --agent-name <agent_name> --message <text> [--session-key <key>]`
- Monorepo bootstrap installer:
  - `scripts/install/bootstrap_monorepo.sh`
- Company workspace bootstrap:
  - `uv run python scripts/company/bootstrap_company_workspace.py --apply --company <slug> --display-name "<Name>" --company-workspace-root <path>`
- Repo-workspace migration:
  - `uv run python scripts/company/migrate_repo_workspace.py --apply --company <slug> --source-workspace-root /home/macos/omniClaw/workspace --company-workspace-root <path>`
- Company-context inspection:
  - `uv run python scripts/company/show_company_context.py --company <slug>`
- Budget action helper:
  - `scripts/budgets/trigger_budget_action.sh`
  - HTTP 4xx responses print the kernel response body for faster operator debugging
- Session cost summary helper:
  - `uv run python scripts/budgets/show_session_cost.py --company <slug> --agent-name <agent_name> --session-key <key>`
- IPC trigger:
  - `scripts/ipc/trigger_ipc_action.sh --apply --action scan_forms`
- Dead-letter replay helper:
  - `scripts/ipc/requeue_dead_letter.sh --apply --workspace-root <workspace_root> --file <dead_letter_file>`
- Workspace-to-DB form sync (authoritative refresh):
  - `uv run scripts/forms/sync_form_types_from_workspace.py`
- API-based workspace sync:
  - `curl -sS -X POST http://127.0.0.1:8000/v1/forms/workspace/sync -H 'content-type: application/json' -d '{"activate": true, "prune_missing": false}'`
- Message acknowledge+archive helper (stage-skill tool):
  - `python <company-workspace-root>/forms/message/skills/read-and-acknowledge-internal-message/scripts/acknowledge_and_archive_message.py --apply --workspace-root <workspace_root> --form-file <form_file>`
- Forms action helper:
  - `scripts/forms/trigger_forms_action.sh`
- Publish workflow from workspace package:
  - `scripts/forms/upsert_workflow_from_workspace.sh --apply --activate --form-type <form_type>`
- Workflow smoke publisher:
  - `scripts/forms/smoke_form_workflows.sh [--apply]`
- Deploy workflow E2E live smoke (preflight + sequential holder runbook):
  - `scripts/forms/smoke_deploy_new_agent_e2e.sh [--company <slug>] [--apply]`
- Skills action helper:
  - `scripts/skills/trigger_skill_action.sh`
- Skill state audit:
  - `uv run python scripts/skills/audit_agent_skill_state.py --company <slug>`
- Prompt log listing helper:
  - `uv run python scripts/runtime/list_prompt_logs.py --company <slug> --agent-name <agent_name> [--limit <n>]`
- Skills wrappers:
  - `scripts/skills/list_master_skills.sh`
  - `scripts/skills/list_active_master_skills.sh`
  - `scripts/skills/draft_master_skill.sh`
  - `scripts/skills/update_master_skill.sh`
  - `scripts/skills/set_master_skill_status.sh`
  - `scripts/skills/list_agent_skill_assignments.sh`
  - `scripts/skills/assign_agent_skills.sh`
  - `scripts/skills/remove_agent_skills.sh`
  - `scripts/skills/sync_agent_skills.sh`

## Repo Structure (relevant)
- `src/omniclaw/budgets/`: waterfall budget engine, budget actions/service, and LiteLLM cap reconciliation
- `src/omniclaw/forms/`: form type registry + decision engine
- `src/omniclaw/instructions/`: AGENTS template management, rendering, and manager-skill policy delegation
- `src/omniclaw/ipc/`: form IPC scanner/router
- `src/omniclaw/skills/`: master-skill catalog lifecycle, assignment, and workspace reconciliation service
- `src/omniclaw/usage/`: LLM usage logging and session export services
- `scripts/budgets/`: budget action helpers
- `scripts/forms/`: form admin/publish/smoke scripts
- `scripts/ipc/`: ipc trigger + read/ack helper
- `scripts/company/`: company workspace bootstrap and migration helpers
- `scripts/company/show_company_context.py`: registry-backed company path/context inspector for operator scripts
- `scripts/install/`: monorepo environment bootstrap helper
- `scripts/skills/`: master-skill lifecycle and assignment action wrappers
- `src/omniclaw/runtime_integration/`: OmniClaw-owned optional runtime hook loaded by Nanobot for usage persistence
- `third_party/nanobot/`: vendored Nanobot runtime package source
- `workspace/`: repo-local seed/migration source for company assets and fixtures
- `<company-workspace-root>/forms/`: approved form workflow JSON packages
- `<company-workspace-root>/forms/<form_type>/skills/`: approved stage skill master copies per form type
- `<company-workspace-root>/master_skills/`: organization-level loose master skills
- `<company-workspace-root>/nanobot_workspace_templates/`: canonical deployed Nanobot workspace template source
- `<company-workspace-root>/nanobots_instructions/`: external instruction template roots per node
- `<company-workspace-root>/form_archive/`: routed-form backup trail
- `~/.omniClaw/config.json`: global OmniClaw registry and company settings source of truth

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
- M12 targeted runtime/package slice: `12 passed` on `PYTEST_ADDOPTS='-s' uv run pytest -q tests/test_runtime_actions.py tests/test_runtime_integration.py tests/test_nanobot_prompt_logging.py`
- M11 targeted regression slice: `35 passed` on `PYTEST_ADDOPTS='-s' uv run pytest -q tests/test_forms_actions.py tests/test_instructions_actions.py tests/test_ipc_actions.py`
- M11 full suite: `94 passed` on `PYTEST_ADDOPTS='-s' uv run pytest -q`
- M11 migration verification: `uv run alembic current` -> `20260315_0014 (head)`
- Strict change validation: `openspec validate --type change m11-master-skill-lifecycle --strict`
- Targeted Nanobot migration slice: `20 passed` on `uv run pytest tests/test_schema_repository.py tests/test_runtime_actions.py tests/test_provisioning_actions.py -q`
- Full suite: `74 passed` on `PYTEST_ADDOPTS='-s' uv run pytest -q`
- Template/inbox rename slice: `30 passed` on `uv run pytest -q tests/test_nanobot_skill_wrappers.py tests/test_ipc_actions.py tests/test_schema_repository.py`
- Strict change validation: `openspec validate --type change m10-waterfall-budget-engine --strict`
- Strict change validation: `openspec validate --type change m07d-template-and-inbox-path-rename --strict`
- Live deploy smoke: `scripts/forms/smoke_deploy_new_agent_e2e.sh --apply --allow-agent-fallback --request-file 2026-03-06-m07b-nanobot-smoke-4.md`
- Manual reprovision retry: kernel `POST /v1/provisioning/actions` returned `200`, `Signal_Cartographer_01` was recreated under `workspace/agents/Signal_Cartographer_01/`, and a direct Nanobot `hello` smoke returned `Hello!`
