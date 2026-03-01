## 1. Schema Foundations

- [x] 1.1 Add SQLAlchemy base, enums, and model definitions for canonical tables.
- [x] 1.2 Add DB session/engine utilities for local SQLite execution.

## 2. Migration Baseline

- [x] 2.1 Initialize Alembic configuration for the project.
- [x] 2.2 Add initial migration creating canonical tables and key constraints.

## 3. Repository and Tests

- [x] 3.1 Implement repository methods for node creation and hierarchy linking.
- [x] 3.2 Add tests that insert HUMAN + AGENT nodes and verify parent-child relationship persistence.

## 4. Verification

- [x] 4.1 Run `uv run pytest -q`.
- [x] 4.2 Run `openspec validate --type change m02-canonical-state-schema --strict`.
