## 1. Schema and Migration Foundation

- [x] 1.1 Add SQLAlchemy models/enums updates for dynamic form typing and lifecycle snapshots (`form_types`, `form_transition_events`, `forms_ledger` bindings).
- [x] 1.2 Create Alembic migration(s) to create new form registry/event tables and apply forms ledger compatibility updates.
- [x] 1.3 Seed bootstrap `message` form type definition and bind legacy MESSAGE ledger rows to snake_case `message`.

## 2. Repository and Decision Engine

- [x] 2.1 Add repository operations for form-type upsert/read/activate/deprecate/delete and append-only decision events.
- [x] 2.2 Implement forms state-machine validation for decision edges and deterministic holder resolution (including terminal `none`).
- [x] 2.3 Implement deterministic form ID generation and collision handling.
- [x] 2.4 Ensure decision operations update snapshot + append decision event atomically.

## 3. Kernel Actions and Operator Tooling

- [x] 3.1 Add `/v1/forms/actions` request schema and wiring for admin/runtime actions.
- [x] 3.2 Add runtime form actions for form creation and decision.
- [x] 3.3 Provide helper scripts under `scripts/forms/` for repeatable form lifecycle operations.

## 4. IPC Integration and Workflow Compatibility

- [x] 4.1 Refactor IPC to route generic forms via active stage-graph definitions.
- [x] 4.2 Keep legacy compatibility alias (`scan_messages`, `type: MESSAGE`) mapped into generic form routing path.
- [x] 4.3 Add dynamic target resolution support (`{{initiator}}`, `{{any}}`, `{{var}}`) and terminal no-holder handling.
- [x] 4.4 Persist routed-form backup copies under `workspace/form_archive/`.
- [x] 4.5 Validate and distribute next-stage required skills from workspace form packages.

## 5. Verification and Regression Coverage

- [x] 5.1 Add/update tests for valid decisions, invalid decisions, holder invariants, and dynamic target routing.
- [x] 5.2 Add integration tests for form admin actions and runtime decisions.
- [x] 5.3 Update IPC tests for form-centric routing path and compatibility alias behavior.
- [x] 5.4 Run `uv run pytest -q`, `openspec validate --type change m06-forms-ledger-state-machine --strict`, and `openspec validate --all --strict`.

## 6. Documentation, Trackers, and Skill Closure

- [x] 6.1 Update `docs/current-task.md`, `docs/plan.md`, `docs/implement.md`, and `docs/documentation.md` with form-centric M06 behavior.
- [x] 6.2 Update `AGENTS.md` repository map for workspace-first form/skill package layout.
- [x] 6.3 Create/update skills for form authoring, stage execution, template authoring, and IPC routing.
- [x] 6.4 Add canonical workspace form packages (`message`, `deploy_new_agent`) and workflow publication smoke tooling.
