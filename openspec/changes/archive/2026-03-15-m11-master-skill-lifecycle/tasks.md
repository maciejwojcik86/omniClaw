## 1. OpenSpec And Tracker Setup

- [x] 1.1 Author the M11 proposal, design, and delta specs for the master skill lifecycle, schema, IPC, provisioning, instructions, and deploy workflow changes.
- [x] 1.2 Update `docs/current-task.md`, `docs/plan.md`, and `docs/implement.md` so `m11-master-skill-lifecycle` is the active change with explicit implementation TODOs.

## 2. Schema And Repository

- [x] 2.1 Add the master-skill lifecycle enum and `node_skill_assignments` schema, including Alembic migration coverage and schema tests.
- [x] 2.2 Extend SQLAlchemy models and repository methods for lifecycle filtering, batch lookup, assignment upsert/remove/list, default-skill resolution, and effective skill queries.

## 3. Skills Service And API

- [x] 3.1 Add a dedicated `src/omniclaw/skills/` service and `/v1/skills/actions` request surface for catalog mutation, assignment mutation, and on-demand reconciliation.
- [x] 3.2 Add canonical wrapper scripts under `scripts/skills/` and new loose company master-skill packages for authoring, managing, and assigning master skills.

## 4. Integration

- [x] 4.1 Replace hardcoded manager-skill distribution with assignment-based reconciliation in provisioning, instructions, and IPC scan pre-pass flows.
- [x] 4.2 Replace direct form stage-skill copies with durable `FORM_STAGE` assignments plus immediate sync for affected nodes during workflow activation and routing.
- [x] 4.3 Seed default loose skills from company config during agent provisioning and update the `deploy-new-nanobot` workflow skill guidance.

## 5. Verification And Skill Capture

- [x] 5.1 Add/extend repository, skills API, provisioning, forms, and IPC tests covering lifecycle states, assignment rules, stray-skill cleanup, and restored approved skills.
- [x] 5.2 Update developer/copilot skill coverage with a mirrored `master-skill-lifecycle` skill and any affected SOPs, plus living documentation and repository map updates.
- [x] 5.3 Run `uv run pytest -q`, `openspec validate --type change m11-master-skill-lifecycle --strict`, and the necessary migration verification commands.
