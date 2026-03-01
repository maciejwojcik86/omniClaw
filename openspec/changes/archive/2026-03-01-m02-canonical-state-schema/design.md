## Context

Milestone M01 established the kernel service skeleton. M02 introduces canonical persistence structures needed by all subsequent features: provisioning, messaging/forms, budgeting, and skills lifecycle.

## Goals / Non-Goals

**Goals:**
- Define strongly typed SQLAlchemy models for the five canonical tables.
- Add first Alembic migration to create these tables.
- Provide repository-level create/query operations for nodes and hierarchy.
- Add integration tests validating insertion and linkage behavior.

**Non-Goals:**
- Implement provisioning workflows or daemon processes.
- Implement full form routing/state machine logic beyond schema shape.
- Integrate with LiteLLM or external systems.

## Decisions

- Use SQLAlchemy 2.x declarative models with Python enums to keep schema readable and testable.
- Start with SQLite compatibility while preserving field structures compatible with PostgreSQL migration.
- Store form history as JSON text for SQLite baseline; defer engine-specific JSON optimization.
- Keep repository API intentionally narrow in M02 (create node, link hierarchy, fetch hierarchy links).

## Risks / Trade-offs

- [Risk] SQLite type behavior differs from PostgreSQL. -> Mitigation: keep core types portable and avoid engine-specific features in M02.
- [Risk] Early enum values may evolve. -> Mitigation: centralize enums in one module to control migration updates.
- [Risk] Minimal repository surface may need refactor in M03+. -> Mitigation: isolate persistence access behind repository classes.
