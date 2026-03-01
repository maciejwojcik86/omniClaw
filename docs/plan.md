# OmniClaw Long-Horizon Plan

This document is the execution plan and decision log for long-horizon OmniClaw delivery.

Guiding principles
- Determinism over convenience.
- Privileged operations behind strict boundaries and test doubles.
- One milestone = one OpenSpec change.
- Docs and trackers updated in the same change as implementation.

## Verification Checklist (keep current)

Core checks after each milestone:
- [ ] `uv run pytest -q`
- [ ] `openspec validate --type change <change-id> --strict`

Checkpoint sweep:
- [ ] `openspec validate --all --strict`

## Milestone Status

| Milestone | Change ID | Phase | Status | Dependencies | Owner | Exit Criteria |
| --- | --- | --- | --- | --- | --- | --- |
| M00 | `m00-governance-bootstrap` | Governance | completed | none | engineering | AGENTS + trackers + OpenSpec config updated; strict validation passes |
| M01 | `m01-kernel-service-skeleton` | Foundation | completed | M00 | engineering | FastAPI app boots; `/healthz` returns 200 |
| M02 | `m02-canonical-state-schema` | Foundation | completed | M01 | engineering | Core tables + enums + migration + insert test |
| M03 | `m03-linux-provisioning` | Foundation | in_progress | M02 | engineering | Provisioning adapters + workspace permissions verified |
| M04 | `m04-agent-runtime-bootstrap` | Foundation | planned | M03 | engineering | Restricted Nullclaw runtime writes to `/drafts` |
| M05 | `m05-file-ipc-router` | Communication Bus | planned | M04 | engineering | Outbox->Inbox route in <=5s with permission checks |
| M06 | `m06-forms-ledger-state-machine` | Communication Bus | planned | M05 | engineering | Form IDs + state transitions + holder/history tracking |
| M07 | `m07-approval-action-executors` | Workflow Automation | planned | M06 | engineering | Approved SPAWN/UPDATE_TEMPLATE trigger side effects |
| M08 | `m08-context-injector` | Context Injection | planned | M07 | engineering | Template vars render to read-only AGENTS within 5s |
| M09 | `m09-litellm-key-management` | Budgeting | planned | M08 | engineering | Virtual keys + cost ingestion persisted per node |
| M10 | `m10-waterfall-budget-engine` | Budgeting | planned | M09 | engineering | Hierarchical allocation enforces strict child quotas |
| M11 | `m11-master-skill-lifecycle` | Skills | planned | M10 | engineering | Validated skill deployment copied to agent `/skills` |
| M12 | `m12-constitution-and-sop-pack` | Soft Domain | planned | M11 | engineering | Constitution + SOP pack integrated and usable by agents |
| M13 | `m13-autonomous-e2e-simulation` | MVP Release Gate | planned | M12 | engineering | End-to-end worker budget request/approval loop succeeds |
| M14 | `m14-matrix-taskforce-workspaces` | Post-MVP | planned | M13 | engineering | Temporary cross-functional workspace provisioning works |
| M15 | `m15-cross-charge-and-internal-audit` | Post-MVP | planned | M14 | engineering | Cross-charge budget flow + audit workflow operational |

## Phase Checklist (Gemini Scavenge)

This compact checklist complements the detailed milestone plan above and is kept for fast session orientation.

### Phase 1: Foundation (Database and Physical OS)
- [x] Step 1: Core database schema.
- [ ] Step 2: Linux user and workspace provisioning.
- [ ] Step 3: Nullclaw bootstrap and manual restricted execution.

### Phase 2: Communication and Context (IPC and Templating)
- [ ] Step 4: Formal form daemon (P2P messaging + frontmatter parsing + routing).
- [ ] Step 5: Context injector daemon (persona template -> rendered AGENTS).

### Phase 3: Financial Control (LiteLLM and Waterfall Budget)
- [ ] Step 6: LiteLLM proxy setup and virtual keys.
- [ ] Step 7: Waterfall budget daemon and quota sync.

### Phase 4: Business Logic (Lifecycles and Master Skills)
- [ ] Step 8: Form workflow routing with revision loops.
- [ ] Step 9: Master skill library and validation lifecycle deployment.

### Phase 5: Managerial Operations and E2E
- [ ] Step 10: Deployment approval workflow (`SPAWN_AGENT`).
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
- Initial template/TODO seed logic.
- Run metadata capture.

Acceptance criteria:
- Restricted runtime produces artifact in worker drafts area.

Verification:
- runtime integration test + smoke command.

### M05 - File IPC router (`m05-file-ipc-router`)
Scope:
- Daemon scans pending outboxes and routes markdown forms/messages.
- Permission checks, sent/dead-letter behavior.

Acceptance criteria:
- A->B route succeeds within target window in integration test.

### M06 - Forms ledger state machine (`m06-forms-ledger-state-machine`)
Scope:
- Form ID generation and transition enforcement.
- Holder tracking + append-only history log updates.

Acceptance criteria:
- SUBMITTED requests are tracked with correct holder and history.

### M07 - Approval action executors (`m07-approval-action-executors`)
Scope:
- Approved `SPAWN_AGENT` triggers provisioning.
- Approved `UPDATE_TEMPLATE` updates template and triggers refresh hook.

Acceptance criteria:
- Both approval flows execute safely and atomically.

### M08 - Context injector (`m08-context-injector`)
Scope:
- Template renderer for time/manager/subordinates/budget/recent run context.
- Read-only AGENTS rendering daemon.

Acceptance criteria:
- DB updates reflected in rendered AGENTS within SLA.

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
- Agent workspaces provide inbox/outbox/notes/journal/drafts/skills boundaries.
- Router and runtime act only within allowed directories.

### 4) Deterministic workflows
- Stable form IDs, explicit transition rules, append-only history entries.
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
