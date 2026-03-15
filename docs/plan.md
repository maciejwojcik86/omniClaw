# OmniClaw Long-Horizon Plan

This document is the execution plan and decision log for long-horizon OmniClaw delivery.

Guiding principles
- Determinism over convenience.
- Privileged operations behind strict boundaries and test doubles.
- One milestone = one OpenSpec change.
- Docs and trackers updated in the same change as implementation.

## Verification Checklist (keep current)

Core checks after each milestone:
- [x] `uv run pytest -q`
- [x] `openspec validate --type change <change-id> --strict`

Checkpoint sweep:
- [x] `openspec validate --all --strict`

## Milestone Status

| Milestone | Change ID | Phase | Status | Dependencies | Owner | Exit Criteria |
| --- | --- | --- | --- | --- | --- | --- |
| M00 | `m00-governance-bootstrap` | Governance | completed | none | engineering | AGENTS + trackers + OpenSpec config updated; strict validation passes |
| M01 | `m01-kernel-service-skeleton` | Foundation | completed | M00 | engineering | FastAPI app boots; `/healthz` returns 200 |
| M02 | `m02-canonical-state-schema` | Foundation | completed | M01 | engineering | Core tables + enums + migration + insert test |
| M03 | `m03-linux-provisioning` | Foundation | completed | M02 | engineering | Provisioning adapters + workspace permissions verified |
| M04 | `m04-agent-runtime-bootstrap` | Foundation | completed | M03 | engineering | Gateway on/off control + runtime metadata + DB runtime-state tracking |
| M05 | `m05-file-ipc-router` | Communication Bus | completed | M04 | engineering | Outbox->Inbox route in <=5s with deterministic validation + target resolution checks |
| M06 | `m06-forms-ledger-state-machine` | Communication Bus | completed | M05 | engineering | Form registry + graph decisions + deterministic holder semantics + append-only history |
| M07 | `m07-deploy-new-agent-e2e` | Workflow Automation | completed | M06 | engineering | `deploy_new_agent` full lifecycle validated with routed `stage_skill`, smoke runbook evidence, and strict verification |
| M07b | `m07b-nanobot-runtime-migration` | Runtime Pivot | completed | M07 | engineering | Nanobot becomes canonical AGENT runtime with repo-local agent directories, updated deploy workflow assets, and strict verification |
| M07c | `m07c-routed-form-agent-hints` | Workflow UX Hardening | completed | M07b | engineering | Routed forms expose kernel-managed `agent` + `target_agent` hints, preserve `target` for dynamic routing input, and verification passes |
| M07d | `m07d-template-and-inbox-path-rename` | Runtime UX Hardening | completed | M07c | engineering | Nanobot template root resolves from `workspace/nanobot_workspace_templates`, delivered forms land in `inbox/new`, and verification passes |
| M08 | `m08-context-injector` | Context Injection | completed | M07d | engineering | Template vars render to read-only AGENTS within 5s |
| M09 | `m09-litellm-key-management` | Budgeting | completed | M08 | engineering | Virtual keys + cost ingestion persisted per node |
| M10 | `m10-waterfall-budget-engine` | Budgeting | completed | M09 | engineering | Hierarchical allocation enforces strict child quotas |
| M10a | `m10a-agentic-workflow-verification-surface` | Budgeting Hardening | active | M10 | engineering | Canonical discovery, invocation, usage reporting, and budget-report workflow validates current implementation end-to-end |
| M11 | `m11-master-skill-lifecycle` | Skills | planned | M10a | engineering | Validated skill deployment copied to agent `/skills` |
| M12 | `m12-constitution-and-sop-pack` | Soft Domain | planned | M11 | engineering | Constitution + SOP pack integrated and usable by agents |
| M13 | `m13-autonomous-e2e-simulation` | MVP Release Gate | planned | M12 | engineering | End-to-end worker budget request/approval loop succeeds |
| M14 | `m14-matrix-taskforce-workspaces` | Post-MVP | planned | M13 | engineering | Temporary cross-functional workspace provisioning works |
| M15 | `m15-cross-charge-and-internal-audit` | Post-MVP | planned | M14 | engineering | Cross-charge budget flow + audit workflow operational |

## Phase Checklist (Gemini Scavenge)

This compact checklist complements the detailed milestone plan above and is kept for fast session orientation.

### Phase 1: Foundation (Database and Physical OS)
- [x] Step 1: Core database schema.
- [x] Step 2: Linux user and workspace provisioning.
- [x] Step 3: Agent runtime bootstrap and manual restricted execution.

### Phase 2: Communication and Context (IPC and Templating)
- [x] Step 4: Formal form daemon (P2P messaging + frontmatter parsing + routing).
- [x] Step 5: Context injector daemon (persona template -> rendered AGENTS).

### Phase 3: Financial Control (LiteLLM and Waterfall Budget)
- [x] Step 6: LiteLLM proxy setup and virtual keys.
- [x] Step 7: Waterfall budget daemon and quota sync.

### Phase 4: Business Logic (Lifecycles and Master Skills)
- [ ] Step 8: Form workflow routing with revision loops.
- [ ] Step 9: Master skill library and validation lifecycle deployment.

### Phase 5: Managerial Operations and E2E
- [ ] Step 10: Deployment workflow (`deploy_new_agent`) E2E hardening and validation.
- [ ] Step 11: Managerial supervision CAPA workflow (`UPDATE_TEMPLATE`).
- [ ] Step 12: Budget request workflow.
- [ ] Step 13: Constitution and core SOP package.
- [ ] Step 14: End-to-end autonomous simulation.

## Milestones (implementation detail)

### M03 - Linux provisioning (`m03-linux-provisioning`)
Scope:
- Provisioner interface with `mock` and `system` adapters.
- Workspace scaffold creation.
- Ownership/group permission assignment behavior.

Key modules:
- `src/omniclaw/provisioning/*`
- `tests/*provisioning*`
- system verification script under `scripts/`.

Acceptance criteria:
- Mock adapter fully testable without privileged host operations.
- System adapter encapsulates command execution safely.
- Workspace tree matches contract.

Verification:
- `uv run pytest -q`
- `openspec validate --type change m03-linux-provisioning --strict`

### M04 - Agent runtime bootstrap (`m04-agent-runtime-bootstrap`)
Scope:
- Runtime wrapper for launching Nullclaw under restricted user.
- Runtime gateway control actions (`gateway_start`, `gateway_stop`, `gateway_status`, `list_agents`).
- Use existing native Nullclaw workspace context files (no M04 prompt seed generation).
- Run metadata capture under drafts output boundary.
- Canonical DB runtime-state tracking on `nodes` (`gateway_running`, pid, host/port, start/stop timestamps).
- Register kernel-running Linux user as HUMAN node with workspace inside repo (`workspace/<user>`).
- Enforce AGENT line manager requirement (manager can be HUMAN or AGENT) and support linking manager for existing AGENT rows.
- Delegated operator SOP via runtime-control skill (`.codex/skills/runtime-gateway-control`).

Acceptance criteria:
- Restricted runtime produces artifact in worker drafts area.
- Gateway enable/disable updates canonical runtime state in DB.
- Operators can control runtime through endpoint-driven scripts/skill.
- HUMAN supervisor node participates in canonical node/hierarchy model with repo-local workspace.
- Baseline hierarchy exists: HUMAN supervisor (`macos`) manages `Director_01`.

Verification:
- `uv run pytest -q`
- `openspec validate --type change m04-agent-runtime-bootstrap --strict`
- `scripts/runtime/smoke_gateway_control.sh` (dry-run or apply depending on environment).

### M05 - File IPC router (`m05-file-ipc-router`)
Scope:
- Router scans queued outbox messages and routes markdown `MESSAGE` forms.
- Minimal frontmatter contract (`type`, `sender`, `target`, `subject`).
- Sender identity derived from workspace ownership; target routing allowed for any registered node with valid workspace.
- Deterministic archive/undelivered behavior with canonical DB lifecycle metadata.
- Developer + agent-facing SOP skills for extensibility and message authoring/submission.

Acceptance criteria:
- A->B route succeeds within target window in integration test.

Verification:
- `uv run pytest -q`
- `openspec validate --type change m05-file-ipc-router --strict`

### M06 - Forms ledger state machine (`m06-forms-ledger-state-machine`)
Scope:
- Form-type registry with versioned lifecycle (`DRAFT`, `VALIDATED`, `ACTIVE`, `DEPRECATED`).
- Graph-driven status decisions with decision forks and next-holder resolution.
- Deterministic form ID generation and collision-safe persistence.
- Single-holder invariant enforcement per form snapshot.
- Append-only decision events for lifecycle history.
- Form-admin control/tooling for create/update/validate/activate/deprecate workflows.
- Stage-level skill references in active form definitions (templates live with skills).

Acceptance criteria:
- Custom form types can be registered and activated without schema changes.
- Valid decisions update snapshot + holder + append-only event history atomically.
- Invalid decisions are rejected with no partial writes.
- MESSAGE lifecycle persistence is delegated to the shared state-machine path.

### M07 - Deploy workflow E2E hardening (`m07-deploy-new-agent-e2e`)
Scope:
- Harden `deploy_new_agent` full lifecycle handoff from `BUSINESS_CASE` to terminal archive.
- Add kernel-managed routed frontmatter `stage_skill` metadata (`""` at terminal no-holder stage).
- Standardize workspace form stage skill naming to hyphen convention.
- Add deterministic integration coverage and operator live-smoke runbook assets.
- Keep deployment action execution stage-owned (`deploy-new-claw-agent`), no kernel auto-provision trigger at approval edge.

Acceptance criteria:
- `stage_skill` present/correct on routed hops and empty on terminal archive.
- Deterministic deploy lifecycle test passes end-to-end.
- Live smoke runbook validates holder sequencing and archive evidence.
- `UPDATE_TEMPLATE` workflow remains explicitly deferred from this change.

### M07b - Nanobot runtime migration (`m07b-nanobot-runtime-migration`)
Scope:
- Replace Nullclaw as the canonical AGENT runtime with Nanobot.
- Move AGENT provisioning from per-agent Linux users to repo-local directories under `workspace/agents/<agent_name>/`.
- Migrate runtime metadata away from `nullclaw_config_path` and cross-user launch assumptions toward canonical Nanobot config/workspace inputs.
- Rewrite canonical deployment assets around `deploy-new-nanobot` while keeping `deploy-new-claw-agent` as an optional legacy path.

Acceptance criteria:
- AGENT nodes can be provisioned without creating dedicated Linux users.
- Runtime start/stop/status uses Nanobot-backed config/workspace inputs.
- `deploy_new_agent` canonical workflow references `deploy-new-nanobot`.
- Tests and operator smoke assets pass against the Nanobot directory contract.
- `uv run pytest -q`
- `openspec validate --type change m07b-nanobot-runtime-migration --strict`

Implementation notes:
- Alembic revision `20260306_0010` renames `nodes.nullclaw_config_path` to `nodes.runtime_config_path`.
- Canonical AGENT directories now live at `workspace/agents/<agent_name>/{config.json,workspace/}`.
- Verified CLI contract: `nanobot gateway` and `nanobot agent` accept explicit `-w/--workspace` and `-c/--config`; `nanobot status` still reports the default home instance only.

### M07c - Routed form agent hints (`m07c-routed-form-agent-hints`)
Scope:
- Add kernel-managed routed frontmatter fields `agent` and `target_agent`.
- Keep routed `target` empty until an agent explicitly sets it for a dynamic route.
- Support multiline frontmatter values for readable decision-to-target hints.
- Align tests and operator/agent instructions with the new routed header contract.

Acceptance criteria:
- Delivered `inbox/new` forms show the current holder via `agent`.
- Delivered forms show decision-to-next-holder hints via `target_agent`.
- Router still resolves `{{initiator}}`, `{{any}}`, and static targets deterministically.
- `uv run pytest -q`
- `openspec validate --type change m07c-routed-form-agent-hints --strict`

### M07d - Template root and inbox path rename (`m07d-template-and-inbox-path-rename`)
Scope:
- Rename the canonical Nanobot workspace template source from its legacy path to `workspace/nanobot_workspace_templates`.
- Rename the delivered inbox folder contract from its legacy path to `inbox/new`.
- Update runtime/config/scaffold helpers, canonical skills/docs, and live workspace copies to the new names.

Acceptance criteria:
- Provisioning and deploy helpers source templates from `workspace/nanobot_workspace_templates`.
- Kernel routing and feedback delivery use `inbox/new`.
- Canonical heartbeat/AGENTS guidance and distributed skill copies point to the renamed paths.
- `uv run pytest -q`
- `openspec validate --type change m07d-template-and-inbox-path-rename --strict`

Archive status:
- Archived as `openspec/changes/archive/2026-03-07-m07d-template-and-inbox-path-rename`.
- Final closure included live workspace durable-memory cleanup for `workspace/agents/Ops_Head_01/workspace/memory/`.

### M08 - Context injector (`m08-context-injector`)
Scope:
- Template renderer for time/manager/subordinates/budget/recent run context.
- Read-only AGENTS rendering daemon.

Acceptance criteria:
- DB updates reflected in rendered AGENTS within SLA.

Implementation notes:
- Store per-node `role_name` and `instruction_template_root` in canonical node metadata.
- Keep source templates outside deployed workspaces under `workspace/nanobots_instructions/<node_name>/`.
- Add kernel instruction actions and a repo-local company config file for `direct_children` vs `descendant` access control.
- Refresh all active AGENT `AGENTS.md` files at the start of each IPC scan cycle; render failures must not block form routing.

### M09 - LiteLLM key management (`m09-litellm-key-management`)
Scope:
- Virtual key lifecycle per node.
- Usage + cost ingestion.

Acceptance criteria:
- Proxied usage is attributable to node and persisted.

### M10 - Waterfall budget engine (`m10-waterfall-budget-engine`)
Scope:
- Hierarchical allocation calculator.
- Strict quota sync and budget request handling hooks.

Acceptance criteria:
- Parent-child percentage allocation enforces expected quota.

Implementation notes:
- `workspace/company_config.json` now carries `budgeting.daily_company_budget_usd`, `budgeting.root_allocator_node`, and `budgeting.reset_time_utc`.
- Canonical DB state now includes `budgets.budget_mode`, `budgets.rollover_reserve_usd`, `budgets.review_required_at`, plus `budget_allocations` and `budget_cycles`.
- `/v1/budgets/actions` now supports `team_budget_view`, `set_team_allocations`, `set_node_budget_mode`, `run_budget_cycle`, and `recalculate_subtree` alongside cost sync actions.
- Kernel lifespan runs a budget maintenance loop for idempotent daily cycle execution and restart catch-up.
- AGENTS rendering now includes budget placeholders and managers receive both `manage-agent-instructions` and `manage-team-budgets`.

Verification:
- `PYTEST_ADDOPTS='-s' uv run pytest -q`
- `openspec validate --type change m10-waterfall-budget-engine --strict`

### M10a - Agentic workflow verification surface (`m10a-agentic-workflow-verification-surface`)
Scope:
- Canonical agent catalog/report surface for active discovery.
- Canonical budget report surface for before/after comparison.
- Kernel-mediated prompt invocation for low-cost verification runs.
- Canonical usage/session summary read APIs and endpoint-backed wrapper scripts.
- Final end-to-end workflow validation using only approved endpoints/scripts.

Acceptance criteria:
- Supervising callers can discover agents, invoke cheap prompts, inspect usage, and compare budget deltas without repo discovery or direct DB access.

Implementation notes:
- Supporting analysis and execution detail live in `docs/agentic-workflow-gap-analysis.md` and `docs/agentic-workflow-implementation-and-test-plan.md`.
- M10a is an explicit confidence gate before `m11-master-skill-lifecycle`; do not advance until the current budget workflow is canonically validated.
- Direct DB readers and repo-local diagnostic scripts may remain for debugging but do not count as the proof-path for completion.

Verification:
- `uv run pytest -q`
- `openspec validate --type change m10a-agentic-workflow-verification-surface --strict`
- canonical end-to-end budget verification runbook executed through approved endpoints/scripts

Current checkpoint:
- Implemented canonical discovery, budget-report, runtime invocation, usage/session read APIs, wrapper scripts, and mirrored verification skill.
- Added deterministic mock-mode usage/spend persistence so the canonical proof path works in environments using approved mock runtime invocation.
- Verified targeted tests: `uv run pytest -q tests/test_usage_actions.py tests/test_runtime_actions.py tests/test_budgets_actions.py` (`22 passed`).
- Verified full suite: `uv run pytest -q` (`87 passed`).
- Canonical wrapper-only E2E passed on 2026-03-11 using approved scripts only; verified usage/session evidence and budget delta for `HR_Head_01` session `cli:m10a-verify-20260311-1435`.
- Additional follow-up hardening is now required before archive: the live usage-reporting path currently relies on customized Nanobot runtime code in an external checkout that directly imports `omniclaw.*` from `nanobot/agent/loop.py`.
- Planned resolution direction: internalize the customized Nanobot runtime into the OmniClaw monorepo, keep automatic runtime-level usage logging, and redesign the coupling boundary so OmniClaw no longer depends on a separately maintained external Nanobot fork.
- M10a should remain active until that coupling decision/work item is properly planned and, if kept in-scope, implemented or explicitly split into the next change.
- Detailed planning draft for the likely follow-up change is captured in `docs/nanobot-monorepo-internalization-openspec-plan.md` (suggested change id: `m10b-nanobot-monorepo-internalization`).

### M11 - Master skill lifecycle (`m11-master-skill-lifecycle`)
Scope:
- Skill registry model + version/checksum.
- Validated-skill deployment daemon.

Acceptance criteria:
- Only validated skill versions are deployed to mapped agents.

### M12 - Constitution and SOP pack (`m12-constitution-and-sop-pack`)
Scope:
- Author constitution and key process SOPs.
- Integrate SOP assets into agent context stack.

Acceptance criteria:
- Agents can produce schema-valid form payloads from SOP guidance.

### M13 - Autonomous E2E simulation (`m13-autonomous-e2e-simulation`)
Scope:
- Director + worker scenario harness.
- Budget exhaustion and request/approval/reallocation loop.

Acceptance criteria:
- Full loop succeeds without invalid form schema or daemon crash.

### Post-MVP M14-M15
Scope:
- Matrix task force workspace provisioning.
- Cross-charge economy and independent audit workflow.

Acceptance criteria:
- Scoped to post-MVP and not started before M13 completion.

## Architecture Overview

### 1) Canonical state model
- Relational schema is the source of truth.
- Filesystem artifacts are operational interfaces, not primary state.

### 2) Kernel API + daemon split
- FastAPI handles control-plane calls and orchestration commands.
- Daemons handle periodic/continuous workloads (routing, rendering, budget sync, deployment).

### 3) Filesystem contract
- Agent workspaces provide inbox/outbox/notes/drafts/skills boundaries.
- Router and runtime act only within allowed directories.

### 4) Deterministic workflows
- Stable form IDs, explicit decision rules, append-only history entries.
- Deterministic rendering of AGENTS templates from live data.

### 5) Budget governance pipeline
- Per-node key identity -> usage ingestion -> allowance calculation -> quota sync.
- Top-down allocation remains auditable.

### 6) Skill governance pipeline
- Draft -> QA -> validated -> deprecated lifecycle.
- Deployment is controlled by lifecycle state and mapping rules.

## Risk Register

1. Privileged provisioning safety risk
- Mitigation: adapter isolation, mock-first tests, manual system verification script.

2. Routing/state race conditions
- Mitigation: idempotent processing, lock strategy, deterministic ordering rules.

3. Template injection drift
- Mitigation: strict variable contract + renderer tests + file immutability policy.

4. Budget quota mismatch (Kernel vs LiteLLM)
- Mitigation: reconciliation job, drift alerting, authoritative write path.

5. Skill supply-chain integrity
- Mitigation: checksum/version policy and deployment from validated registry only.

6. Long-horizon context drift
- Mitigation: mandatory updates to `docs/plan.md`, `docs/documentation.md`, and trackers per milestone.

7. Nanobot CLI/runtime contract drift
- Mitigation: validate the installed Nanobot binary against the verified `/home/macos/.nanobot/` reference before freezing runtime command templates or smoke scripts.

## Demo Script (3-5 minutes)

1. Show governance and traceability
- Open `docs/current-task.md`, `docs/plan.md`, and active OpenSpec change.

2. Show service baseline
- Start service, call `/healthz`.

3. Show canonical state integrity
- Run migration + tests demonstrating HUMAN->AGENT hierarchy linkage.

4. Show provisioning workflow (when M03 completes)
- Run mock provisioning test and manual system check steps.

5. Show end-to-end autonomy path (M13)
- Worker runs out of budget, submits form, manager approves, quota updates, worker continues.

## Implementation Notes

- 2026-03-01: M00-M02 complete and archived; M03 created and active.
- 2026-03-01: Added long-horizon control docs (`docs/prompt.md`, `docs/plan.md`, `docs/implement.md`, `docs/documentation.md`) based on OpenAI long-horizon Codex guidance and adapted to OpenSpec workflow.
- 2026-03-01: Merged former `docs/master-task-list.md` into `docs/plan.md` to keep one canonical planning source.
- 2026-03-01: Adopted mandatory skill-first modular provisioning workflow; added project-local skills and helper scripts for user creation, workspace scaffold, and permission policy.
- 2026-03-01: Added privileged provisioning helper allowlist pattern and system adapter helper integration for endpoint-driven host actions with SQLite node tracking.
- 2026-03-01: Consolidated provisioning skills into `.codex/skills/deploy-new-claw-agent` and added `scripts/provisioning/list_agents_permissions.py` audit report script.
- 2026-03-01: Verified real system provisioning flow end-to-end (Linux user `agent_director_01`, workspace scaffold, permissions, and SQLite node tracking) via `/v1/provisioning/actions`.
- 2026-03-01: Archived OpenSpec change `m03-linux-provisioning` as `2026-03-01-m03-linux-provisioning`; M03 marked complete.
- 2026-03-01: Created active change `m04-agent-runtime-bootstrap` and authored proposal/spec/design/tasks with launch strategy options and pending Nullclaw command-contract inputs.
- 2026-03-01: Aligned M04 and provisioning workflow paths with Nullclaw defaults: config at `~/.nullclaw/config.json` and workspace at `~/.nullclaw/workspace`.
- 2026-03-01: Added Alembic revision `20260301_0002` to track agent runtime metadata in `nodes` (`linux_username`, `linux_password_hash`, workspace root, config path, and primary model) and added `.codex/skills/alembic-migration-ops`.
- 2026-03-01: Added Alembic revision `20260301_0003` to rename `linux_password_hash` to `linux_password` (plaintext reference) and enforce one line manager per child node (`uq_hierarchy_child_manager`).
- 2026-03-01: Updated deploy workflow for shared Nullclaw binaries: one root-managed install under `/opt/omniclaw` plus per-user symlink linking in `~/.local/bin/nullclaw`.
- 2026-03-01: Added troubleshooting SOPs to deploy/runtime skills and introduced `scripts/provisioning/sync_nullclaw_auth.sh` to resolve `AllProvidersFailed` caused by missing per-user auth context.
- 2026-03-03: Refined M04 scope to remove prompt-seed creation and rely on native Nullclaw context files (`AGENTS.md`, `SOUL.md`, `USER.md`, etc.); deferred formal prompt-definition/onboarding-skill work to later milestone backlog.
- 2026-03-03: Implemented M04 runtime control surface (`/v1/runtime/actions`) with gateway start/stop/status/list, metadata capture under `drafts/runtime/runs`, Alembic revision `20260303_0004` for node gateway-state fields, smoke scripts under `scripts/runtime/`, and new delegated runtime SOP skill `.codex/skills/runtime-gateway-control`.
- 2026-03-03: Extended M04 provisioning baseline with `register_human` and `set_line_manager` actions; enforced manager requirement on `provision_agent` (manager node can be HUMAN or AGENT); added one-time HUMAN supervisor bootstrap (`workspace/macos`) and linked `Macos_Supervisor` -> `Director_01` in SQLite hierarchy.
- 2026-03-03: Archived OpenSpec change `m04-agent-runtime-bootstrap` as `2026-03-03-m04-agent-runtime-bootstrap`; M04 marked complete and ready to hand off to M05 planning.
- 2026-03-03: Started M05 change `m05-file-ipc-router`; authored proposal/spec/design/tasks, validated with `openspec validate --type change m05-file-ipc-router --strict`, and set initial contract for minimal `MESSAGE` frontmatter + canonical DB lifecycle tracking + developer/agent message workflow skills.
- 2026-03-03: Implemented M05 IPC routing (`/v1/ipc/actions`), added `forms_ledger` message metadata migration (`20260303_0005`), added integration tests for success/invalid routes, published `ipc-router-development` and `send_message` skills, and archived change as `2026-03-03-m05-file-ipc-router`.
- 2026-03-03: Completed real-host M05 workflow validation: HUMAN `Macos_Supervisor` -> AGENT `Director_01` message delivery via `outbox/send`, Director reply routed back to HUMAN inbox, and lifecycle evidence verified in filesystem + `forms_ledger`.
- 2026-03-03: Closed instruction drift causing agent replies to land in `drafts/` by updating provisioning AGENTS template to require MESSAGE drafts in `outbox/drafts/` and submit in `outbox/send/`.
- 2026-03-03: Created active change `m06-forms-ledger-state-machine`, authored proposal/spec/design/tasks for generic form registry + graph lifecycle + admin tooling + stage skill linkage, and validated with `openspec validate --type change m06-forms-ledger-state-machine --strict`.
- 2026-03-03: Implemented M06 core: added `/v1/forms/actions`, `src/omniclaw/forms` state-machine service, `form_types` + `form_transition_events` schema/migration (`20260303_0006`), deterministic form ID collision policy, snake_case form type keys (built-in `message`), IPC lifecycle integration through forms engine, helper tooling under `scripts/forms/`, templates under `templates/forms/`, and new skills for form-type authoring/stage execution/template authoring. Verified with `uv run pytest -q` and strict OpenSpec validation.
- 2026-03-03: Refined M06 holder/routing semantics: MESSAGE routing now allows any registered target node, built-in `message` lifecycle uses `WAITING_TO_BE_READ -> ARCHIVED` via explicit read acknowledgement, and workflow edges now support deterministic named-holder (`static_node_name`) plus terminal no-holder (`none`) decisions.
- 2026-03-03: Removed runtime graph overwrite for `message` form type: IPC now resolves lifecycle behavior from active `form_types` definition/version, bootstrap-seeding defaults only when no `message` definition exists; added regression test proving custom active `message` workflow drives status decisions.
- 2026-03-03: Simplified message transport failure handling: removed dead-letter routing mutations from IPC scan path; undelivered files remain in `outbox/send` with explicit failure reason in scan output while canonical lifecycle DB writes occur only for successful deliveries.
- 2026-03-03: Added configurable deployment-approval form example `nullclaw_agent_deployment_request_form` (requester draft -> human review -> reject loop/resubmit or terminal approval), shipped requester/reviewer stage skills with templates, added canonical form definitions under `forms/`, and added integration test coverage for submit/reject/resubmit/approve holder decisions.
- 2026-03-03: Added operator smoke runner `scripts/forms/smoke_nullclaw_agent_deployment_request.sh` to execute end-to-end deployment-request lifecycle (upsert/validate/activate/create/submit/reject/resubmit/approve) in dry-run or apply mode.
- 2026-03-03: Executed live apply-mode deployment-request smoke against local kernel (`Director_01` requester, `Macos_Supervisor` reviewer); confirmed terminal form snapshot `APPROVED_FOR_DEPLOYMENT` with `current_holder_node=NULL` and 5 append-only decision events in `form_transition_events`.
- 2026-03-03: Adopted node-centric workflow schema for forms (`start_node`, `end_node`, per-node `status`/`stage_skill_ref`/`holder`, decision edges), kept legacy graph compatibility for existing records, moved approved form definition payloads to repository-root `forms/`, and removed stale `scripts/forms/examples/` JSON files.
- 2026-03-04: Refocused M06 on form-centric IPC routing (`scan_forms` primary, `scan_messages` alias), where `message` is a normal form type. IPC now routes by `workflow_graph.stages`, supports dynamic targets (`{{initiator}}`, `{{any}}`, `{{var}}`), writes backup copies to `workspace/form_archive/`, and distributes required stage skills from `workspace/forms/<form_type>/skills/<required_skill>/`.
- 2026-03-04: Shifted canonical workflow artifacts to `workspace/forms/` packages (removed legacy root `templates/` artifacts), added master authoring skill under `workspace/master_skills/form_workflow_authoring/`, added workflow publisher/smoke scripts in `scripts/forms/`, and added canonical workspace form packages for `message` and `deploy_new_agent`.
- 2026-03-04: Moved default SQLite path from repo root to `workspace/omniclaw.db`; updated runtime config, Alembic default URL, and operator scripts/skills to use the workspace DB location; verified DB remains at Alembic head (`20260303_0007`) with `form_types` present.
- 2026-03-04: Simplified canonical `message` workflow to terminal `WAITING_TO_BE_READ` and added `scripts/forms/sync_form_types_from_workspace.py` to make `form_types` definitions authoritative from `workspace/forms`; synced DB and pruned stale definitions.
- 2026-03-04: Added kernel lifespan IPC auto-scan loop (default enabled, 5s interval) that executes the same routing path as `scan_forms`; confirmed live routing of `workspace/macos/outbox/send/2026-03-04-macos-director-routing-smoke.md` to `Director_01`.
- 2026-03-04: Updated `message` read-stage workflow back to explicit `WAITING_TO_BE_READ -> ARCHIVED` acknowledge decision and replaced read-stage SOP with single script tool `acknowledge_and_archive_message.py` (endpoint call + frontmatter stage update + unread->read move + master archive copy). Hardened `sync_form_types_from_workspace.py` prune logic to preserve versions still referenced by `forms_ledger`.
- 2026-03-05: Archived change `m06-forms-ledger-state-machine` as `2026-03-05-m06-forms-ledger-state-machine` (spec sync was skipped during archive due delta header mismatch in upstream OpenSpec auto-sync).
- 2026-03-06: Created active change `m07b-nanobot-runtime-migration` after deciding to replace the Nullclaw + per-agent Linux-user model with Nanobot repo-local agent directories. Repo review identified the main impact in node runtime metadata, provisioning/runtime services, deploy-stage skill packages, and operator/reference documentation.
- 2026-03-06: Implemented the Nanobot schema/runtime pivot core: renamed node runtime metadata to `runtime_config_path`, moved AGENT provisioning to repo-local `workspace/agents/<agent_name>/workspace`, and added Nanobot config scaffolding with targeted schema/runtime/provisioning tests passing (`20 passed`).
- 2026-03-06: Switched the canonical `deploy_new_agent` stage skill to `deploy-new-nanobot`, rewrote the Nanobot deployment skill package, and retargeted the deploy smoke runner to explicit `nanobot agent/gateway -w -c` invocations instead of Linux-user `nullclaw` execution.
- 2026-03-06: Implemented the core M07b schema/runtime pivot: `runtime_config_path` replaced `nullclaw_config_path`, AGENT provisioning now scaffolds repo-local Nanobot directories under `workspace/agents/<agent_name>/`, gateway commands use explicit Nanobot `--workspace/--config` inputs, and Alembic migration `20260306_0010` preserves existing config-path data.
- 2026-03-06: Rewrote the canonical `deploy-new-nanobot` stage skill, added `scripts/provisioning/deploy_new_nanobot_agent.sh`, updated deploy workflow/IPC tests to target `deploy-new-nanobot`, and retargeted the deploy smoke runner away from `sudo -u ... nullclaw`.
- 2026-03-06: Reprovisioned the canonical sample agents (`Director_01`, `HR_Head_01`, `Ops_Head_01`) into `workspace/agents/...`, synced the active `deploy_new_agent` workflow from workspace so `deploy-new-nanobot` is the routed stage skill, fixed Nanobot deploy/smoke helper gaps (`init_nanobot_config.py` import bootstrap, local workspace scaffold creation, final archive assertions), and completed an apply-mode deploy smoke against the repo-local Nanobot directories.
- 2026-03-06: Archived `m07b-nanobot-runtime-migration` as `2026-03-06-m07b-nanobot-runtime-migration`, synced delta specs into the main OpenSpec tree (`agent-runtime-bootstrap`, `linux-provisioning`, `deploy-new-agent-workflow`), reran strict validation, and reconfirmed local reprovisioning by recreating `Signal_Cartographer_01` through the live kernel endpoint with a successful Nanobot `hello` smoke.
- 2026-03-05: Implemented hardening change `hardening-runtime-ipc-core`: strict runtime host validation, safer gateway command rendering, bounded IPC scan traversal with event-loop offload, `forms_ledger.version` optimistic lock migration (`20260305_0008`), deterministic transition conflict mapping, and startup migration-head enforcement (no runtime `create_all` path). Regression suite updated and passing (`46 passed`).
- 2026-03-05: Archived change `hardening-runtime-ipc-core` as `2026-03-05-hardening-runtime-ipc-core`; synced new/updated specs including `runtime-ipc-hardening`.
- 2026-03-05: Implemented change `ipc-invalid-feedback-and-dedupe`: undelivered forms now dead-letter once, kernel emits structured feedback artifacts (`target` first with sender fallback), IPC response includes `dead_letter_path`/`feedback_path`, added replay script `scripts/ipc/requeue_dead_letter.sh`, and deduped node resolver + manager-link repository logic.
- 2026-03-05: Archived change `ipc-invalid-feedback-and-dedupe` as `2026-03-05-ipc-invalid-feedback-and-dedupe`; synced specs `ipc-invalid-feedback-routing`, `file-ipc-router`, and `canonical-state-schema`.
- 2026-03-05: Added endpoint `POST /v1/forms/workspace/sync` to scan `workspace/forms/*/workflow.json`, validate targets/skills against current node registry and master skill copies, then upsert/activate changed definitions in `form_types` while keeping workflow graph in DB for runtime lookup. Added integration coverage in `tests/test_forms_actions.py`; full suite passing (`50 passed`).
- 2026-03-05: Opened M07 change `m07-deploy-new-agent-e2e` and authored proposal/design/spec/tasks focused on `deploy_new_agent` E2E validation, routed `stage_skill` metadata, hyphen skill naming, and live smoke assets; deferred `UPDATE_TEMPLATE` explicitly.
- 2026-03-05: Implemented routed `stage_skill` write/overwrite behavior in IPC, added full-cycle deploy IPC integration coverage, migrated workspace form `required_skill` names/folders to hyphen convention, added deploy-stage director-seed config template + SOP updates, and introduced `scripts/forms/smoke_deploy_new_agent_e2e.sh` runbook.
- 2026-03-07: Completed active change `m08-context-injector`. Implemented the new context injector daemon to render agent instructions. Modified agent runtime tracking, provisioning service and database (added `role_name` and `instruction_template_root` metadata). Instructions are now saved to `workspace/nanobots_instructions/`, with dynamic variables like manager mapping handled automatically during the new pre-pass inside `scan_forms`. Tested via `test_provisioning_actions.py` and `test_instructions_actions.py`.
- 2026-03-08: Completed active change `m09-litellm-key-management`. Updated `config.py` for LiteLLM master key and proxy URL; created `LiteLLMClient` to wrap `/key/generate`, `/user/info`, and `/user/update` endpoints; wired `ProvisioningService` to generate and persist `virtual_api_key` to `budgets` table and inject into agent `config.json`. Implemented `budgets_actions` endpoint for cost sync and max limit adjustments; added `manage-agent-budgets` Skill SOP. Tests pass and OpenSpec validation is strict.
- 2026-03-08: Completed active change `m09b-usage-and-session-tracking`. Intercepted LLM usage metrics natively from `nanobot/agent/loop.py` to stream token spend and timings into `agent_llm_calls` SQLite table. Authored `POST /v1/sessions/export` to extract local JSONL conversation history to an external directory and tracked export jobs in `agent_session_exports`. Tested passing endpoints and successfully ran `openspec validate --strict`.
- 2026-03-08: Applied runtime hardening after live budget-lookup failures: fixed the UTC reset-time comparison in `BudgetEngine.due_cycle_date`, changed `main.py` to avoid duplicate app imports and to auto-start a loopback-configured LiteLLM proxy, and taught the budget helper/manager skill docs to emit a direct `uv run python main.py` recovery path when the kernel is down.
- 2026-03-08: Hardened live manager budget operations after reproducing Director allocation failures. `BudgetAllocationInput` now accepts alias fields used by agents/operators (`agent_name`, `node_id`, `share_percent`), the trigger helper prints kernel 4xx bodies, and budget recomputation no longer fails closed when LiteLLM `/user/update` is unavailable; those provider issues are returned in `sync_errors` while the kernel-side allocation update still succeeds.
