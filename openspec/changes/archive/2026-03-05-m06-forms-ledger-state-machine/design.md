## Context

M05 introduced deterministic MESSAGE transport and lifecycle persistence, but decision logic is embedded in IPC service code and not reusable across form types. The project now needs a generic forms workflow layer that supports organization-defined form types, branchable lifecycle graphs, and auditable ownership decisions with deterministic holder rules.

Current constraints:
- `forms_ledger` stores current snapshot fields and a JSON `history_log`, but decision semantics are not centrally enforced.
- Form type and status are currently modeled as Python enums, which blocks dynamic custom form types and custom status graphs.
- MESSAGE routing must remain operational while transitioning to generic workflow mechanics.

Stakeholders:
- Operators defining company workflows.
- HUMAN/AGENT nodes executing workflow stages.
- Future milestones (M07+) that depend on deterministic approval state decisions.

## Goals / Non-Goals

**Goals:**
- Add canonical form-type registry and versioned workflow graph definitions.
- Enforce graph-valid decisions, decision branches, and deterministic holder invariant (single holder for active handoff stages, optional no-holder for terminal/automation stages).
- Persist append-only decision events for complete audit history.
- Provide kernel action tooling to create/update/validate/activate/deprecate form types in DB.
- Allow stage-level skill references so each stage can point agents to execution SOP; templates are maintained in skill packages.
- Keep MESSAGE routing behavior compatible while migrating lifecycle writes to the shared decision engine.

**Non-Goals:**
- Execute side-effect actions for approved forms (M07).
- Implement full skill validation/deployment pipeline semantics (M11).
- Build UI management panels; M06 focuses on API + scriptable operator tooling.

## Decisions

### 1) Use canonical registry table for form types and versions
- **Decision:** Introduce `form_types` table with snake_case `type_key`, `version`, lifecycle state, workflow graph JSON, stage metadata JSON, and validation metadata.
- **Rationale:** Supports dynamic/custom form types without schema migrations for each new workflow.
- **Rejected alternative:** Hardcode each form type/status in Python enums and migrations; rejected due to low extensibility and high operational friction.

### 2) Split current snapshot from append-only history
- **Decision:** Keep `forms_ledger` as current snapshot and add `form_transition_events` append-only table for state changes.
- **Rationale:** Snapshot queries stay efficient while preserving immutable audit trail and deterministic replay.
- **Rejected alternative:** Store all history in mutable `forms_ledger.history_log` JSON only; rejected due to weak audit guarantees and difficult querying.

### 3) Validate form status/type via registry, not static enums
- **Decision:** Replace enum-constrained workflow fields with registry-constrained string fields (`form_type_key`, `current_status`) validated by decision service against bound form type version.
- **Rationale:** Required for custom form types and custom status names.
- **Rejected alternative:** Keep static `FormType`/`FormStatus` enums and map custom workflows indirectly; rejected due to complexity and inability to represent arbitrary custom status graphs.

### 4) Enforce deterministic holder invariant at decision boundary
- **Decision:** Every successful decision resolves holder ownership using edge-defined strategy (`static_node`, `static_node_name`, `field_ref`, `previous_holder`, `previous_actor`, `none`) and persists holder change atomically with event append.
- **Rationale:** Aligns with organizational handoff model while allowing explicit terminal or automation states that have no active holder.
- **Rejected alternative:** Infer terminal/no-holder semantics implicitly from status names; rejected because it creates ambiguous and brittle behavior.

### 5) Keep workflow graph as stage-centric JSON with strict schema validation
- **Decision:** Persist stage-graph workflow JSON in `form_types` (`start_stage`, `end_stage`, `stages`) and validate shape/reachability before activation.
- **Rationale:** Flexible branching while matching markdown frontmatter runtime model (`stage`, `decision`, `target`).
- **Rejected alternative:** Normalize every node/edge/stage into many relational tables in M06; rejected to reduce initial complexity and speed delivery.

### 6) Add dedicated forms admin action surface and script helper
- **Decision:** Add `/v1/forms/actions` with deterministic actions: `upsert_form_type`, `validate_form_type`, `activate_form_type`, `deprecate_form_type`, and `transition_form`/`create_form` runtime actions as needed by services.
- **Rationale:** Gives operators and automation a stable control path; scripts can call this endpoint for repeatable workflows.
- **Rejected alternative:** Direct SQL edits for workflow configuration; rejected for safety and auditability reasons.

### 7) Require workspace-backed stage skills in active definitions
- **Decision:** Each stage declares `required_skill`; activation validates master copy at `workspace/forms/<form_type>/skills/<required_skill>/SKILL.md`.
- **Rationale:** Keeps routing graph and execution SOP package coupled and deployable to participants.
- **Rejected alternative:** Store templates/skill content directly inside DB graph payload; rejected for maintainability and version-control ergonomics.

### 8) Treat message as a regular form type
- **Decision:** Keep `message` as a normal workflow package (`workflow.json` under `workspace/forms/message/`, stage skills under `workspace/forms/message/skills/`) and load it through the same registry/state-machine path as any other form type.
- **Rationale:** Avoids special routing subsystems and keeps IPC generic.
- **Rejected alternative:** Maintain message-only code paths in IPC; rejected because it blocks extensibility.

## Risks / Trade-offs

- [Risk] JSON-configured workflows may admit subtle invalid graphs. -> Mitigation: strict activation validator (reachability, decision uniqueness, holder rule validation).
- [Risk] Migration from enum-constrained models can introduce compatibility bugs in repository/service code. -> Mitigation: staged tests plus backward-compatible read/write adapters during M06.
- [Risk] Decision engine becomes central failure point. -> Mitigation: keep API surface small, add unit + integration coverage for all rejection paths.
- [Risk] Stage skill references may drift from filesystem reality. -> Mitigation: skill delta review updates in the same change and operator validation checks.
- [Risk] Backfilling legacy MESSAGE history into events could be lossy. -> Mitigation: preserve original `history_log` for reference and backfill best-effort ordered events with source marker.

## Migration Plan

1. Add Alembic migration(s):
   - Create `form_types` table.
   - Create `form_transition_events` table.
   - Add `form_type_key`, `form_type_version`, and `current_status` string compatibility fields to `forms_ledger` if needed.
2. Seed built-in active `message` form type definition (graph + stage metadata refs).
3. Backfill existing `forms_ledger` MESSAGE rows:
   - Bind `form_type_key=message`, `form_type_version=1.0.0`.
   - Parse existing `history_log` and append corresponding decision events where possible.
4. Implement decision service and repository APIs.
5. Rewire IPC router to process generic forms through stage-graph decisions.
6. Add forms admin endpoint actions and workspace workflow publish helper scripts.
7. Add/refresh workspace form packages and stage skills for authoring/execution.
8. Validate with tests and strict OpenSpec checks.

Rollback strategy:
- If migration fails before cutover, downgrade Alembic revision.
- If runtime issues appear post-cutover, disable forms action usage and keep IPC scan endpoint operational while reverting code to pre-M06 tag.
- Preserve original `history_log` to avoid irreversible audit loss during rollout.

## Open Questions

- What authorization policy should govern AGENT-initiated form-type mutations versus HUMAN/operator-only actions?
- Should activation enforce existence of referenced skill files on disk or only registry references?
- Should per-stage payload schema validation be JSON Schema in M06 or deferred to a lighter required-fields contract?
- Should `form_transition_events` store full payload snapshots or only deltas + hash references in M06?
