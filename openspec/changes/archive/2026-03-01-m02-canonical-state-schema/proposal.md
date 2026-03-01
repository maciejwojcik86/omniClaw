## Why

OmniClaw needs a canonical relational state model before provisioning, routing, budgeting, and approval workflows can be implemented safely. Without a concrete schema and migration path, downstream milestones cannot be built or validated reliably.

## What Changes

- Add SQLAlchemy model definitions for the five canonical tables: `nodes`, `hierarchy`, `budgets`, `forms_ledger`, and `master_skills`.
- Add enum definitions for node types/statuses, form types/statuses, and skill lifecycle states.
- Initialize Alembic migration scaffolding and add the first migration creating canonical tables.
- Add repository utilities and tests proving HUMAN + AGENT insertion and parent-child hierarchy linkage.

## Capabilities

### New Capabilities
- `canonical-state-schema`: Establishes canonical DB schema, enums, migrations, and baseline repository access.

### Modified Capabilities
- None.

## Impact

- Adds DB and migration modules under `src/omniclaw`.
- Adds Alembic configuration and migration scripts.
- Adds tests covering canonical schema integrity and relationship behavior.
