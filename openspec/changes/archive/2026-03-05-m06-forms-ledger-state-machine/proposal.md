## Why

M05 established deterministic MESSAGE transport, but form lifecycle behavior is still encoded ad hoc in router logic. M06 is needed now to introduce a generic, auditable workflow engine so teams can define custom form types, branching approvals, and stage ownership without code changes per workflow.

## What Changes

- Introduce a generic forms state-machine engine that enforces graph-defined decisions, decision forks, and deterministic holder ownership (including explicit terminal no-holder states).
- Add a form-type registry with lifecycle controls so standard and custom form types can be created, versioned, validated, activated, and deprecated from canonical DB state.
- Enforce snake_case form type keys (for example `message`, `feature_pipeline_form`) to encourage specific, composable workflow definitions.
- Add append-only decision event tracking for form lifecycle history, while preserving `forms_ledger` as current snapshot state.
- Add admin control tooling (kernel action + helper script) to create/update/activate/deprecate form-type definitions and stage metadata in DB.
- Add stage-level metadata links for skill guidance so each status can point to SOP instructions; templates are maintained within the referenced skill packages.
- Integrate MESSAGE routing flow with the new state-machine APIs so status/holder/history updates are uniform and no longer hand-built per code path while canonical form type key uses snake_case `message`.
- Publish reusable skills for defining new form types, stage execution guidance, and form template authoring.

In scope:
- Graph-configured status decisions and holder resolution.
- Deterministic form ID policy and collision-safe persistence.
- Canonical DB structures for form type definitions and append-only decision events.
- Snake_case form type key policy and compatibility mapping for existing uppercase MESSAGE ledger rows.
- Tests covering valid decisions, invalid decisions, forks, holder invariants, and MESSAGE regression compatibility.

Out of scope:
- Executing side effects for approved operational forms (`SPAWN_AGENT`, `UPDATE_TEMPLATE`) beyond decision persistence (M07).
- Full master-skill validation/deployment lifecycle automation (M11).
- Budget transfer execution hooks in workflow decisions (post-M07 milestones).

## Capabilities

### New Capabilities
- `forms-ledger-state-machine`: Graph-driven decision enforcement, deterministic form IDs, deterministic holder ownership (single holder or explicit terminal none), and append-only form decision history.
- `form-type-registry`: Canonical form-type definition lifecycle with versioned status graph configs, stage skill linkage, and validation/activation states.
- `form-admin-control`: Kernel action path and helper tooling for creating/updating/activating/deprecating form type definitions in DB.

### Modified Capabilities
- `canonical-state-schema`: Extend canonical schema with form-type registry and append-only form decision event entities, plus related enum/state constraints.
- `file-ipc-router`: Route MESSAGE lifecycle updates through the forms state-machine service instead of ad hoc status/history construction.

## Impact

Affected code and systems:
- Database schema/migrations: `forms_ledger` integration, new registry/event tables, enum updates.
- Repository/domain services: new decision engine and form-type CRUD/validation APIs.
- Kernel API: new form-admin action(s) and IPC integration with lifecycle engine.
- Skills/docs/scripts: new authoring/execution/template skills and helper script(s) for form-type management.
- Tests: repository + service + endpoint integration coverage for graph decisions and MESSAGE compatibility.
