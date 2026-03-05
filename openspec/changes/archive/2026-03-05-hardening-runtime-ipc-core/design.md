## Context

The kernel currently starts runtime gateway commands via shell script composition and executes periodic IPC scans inside the app lifespan task using synchronous scan code. Form transitions rely on read-check-write and `max(sequence)+1` allocation that can race under concurrent writers. Startup still calls `create_all`, which can hide migration drift and bypass Alembic governance.

This change hardens these paths while preserving API shapes and existing operator workflows.

## Goals / Non-Goals

**Goals:**
- Prevent runtime gateway host command injection.
- Keep IPC scan latency bounded under large pending queues and reduce event-loop blocking.
- Ensure concurrent transition attempts produce deterministic conflicts, not duplicate or corrupted event ordering.
- Enforce Alembic-governed schema state at startup.

**Non-Goals:**
- Redesign IPC invalid-form delivery policy.
- Introduce distributed locking or cross-process coordination infrastructure.
- Replace SQLite-first baseline with another datastore.

## Decisions

### 1) Runtime command hardening via validated host + argv composition
- **Decision:** Validate `gateway_host` using strict IP/hostname validation and build launch command from sanitized tokens; reject invalid host at request-validation boundary.
- **Rationale:** Removes high-risk shell metacharacter injection vectors while keeping existing runtime command-template flexibility.
- **Rejected alternative:** Keep shell template interpolation with ad hoc escaping. Rejected because shell escaping is brittle and easy to bypass.

### 2) IPC auto-scan bounded traversal + thread offload
- **Decision:** Exit traversal loops as soon as scan limit is reached and run periodic scan execution through `asyncio.to_thread(...)`.
- **Rationale:** Ensures bounded work per tick and avoids blocking the event loop during filesystem traversal/parsing.
- **Rejected alternative:** Keep full in-loop synchronous scan and only tune interval. Rejected because it does not cap burst latency.

### 3) Optimistic locking on `forms_ledger`
- **Decision:** Add a version column to form snapshot rows and use compare-and-swap style updates for transition writes; map conflicts to deterministic 409 behavior.
- **Rationale:** Low-complexity concurrency control compatible with SQLite and PostgreSQL paths.
- **Rejected alternative:** Pessimistic row locks / SELECT FOR UPDATE semantics. Rejected due to SQLite limitations and portability complexity.

### 4) Migration-first startup gate
- **Decision:** Remove runtime `create_all` startup path and fail startup when DB revision is not at Alembic head.
- **Rationale:** Keeps schema authority with migrations and prevents drift.
- **Rejected alternative:** Keep `create_all` as fallback in development. Rejected because drift bugs leak into tests and operations.

## Risks / Trade-offs

- [Risk] Some existing local DBs may fail startup after the migration gate is added. -> Mitigation: clear startup error with `alembic upgrade head` instruction.
- [Risk] Version-column conflicts may surface in previously silent race paths. -> Mitigation: explicit 409 handling and deterministic retry guidance.
- [Risk] Host validation may reject unusual but valid local host labels. -> Mitigation: implement RFC-aligned hostname pattern and add tests for expected internal hostnames.

## Migration Plan

1. Add Alembic revision for `forms_ledger.version` (or equivalent optimistic lock field) and backfill default values.
2. Update repository transition write path to use version-checked update and unique sequence retry/conflict handling.
3. Update runtime schema/service validation and launch logic.
4. Update app startup to remove implicit `create_all` and enforce revision check.
5. Update tests to initialize DB via Alembic where startup checks require migrated schema.
6. Run `uv run pytest -q` and strict OpenSpec validation.

Rollback strategy:
- Revert code + migration in single change rollback if startup failures are unacceptable.
- For runtime host validation regressions, temporarily constrain accepted host defaults to loopback while fixing parser edge cases.

## Open Questions

- Whether to include bounded automatic retries for transition conflicts in this change or return 409 immediately (default: return 409).
- Whether migration-gate can be bypassed in `OMNICLAW_ENV=test` (default: no bypass; tests should migrate schema explicitly).
