## 1. Runtime and IPC Hardening

- [x] 1.1 Add strict `gateway_host` validation in runtime action schema and adjust runtime command-building path to avoid shell-injection vectors.
- [x] 1.2 Update IPC scan traversal to stop immediately when `scanned == limit` and ensure skipped counting remains deterministic.
- [x] 1.3 Run background IPC auto-scan via non-blocking thread offload (`asyncio.to_thread`) from app lifespan loop.

## 2. Concurrency and Startup Governance

- [x] 2.1 Add optimistic lock metadata to `forms_ledger` via SQLAlchemy model and Alembic migration.
- [x] 2.2 Update form transition repository/service paths to enforce optimistic conflict detection and map stale writes to deterministic HTTP 409.
- [x] 2.3 Remove implicit `create_all` startup behavior and enforce Alembic-head revision check with explicit migration guidance error.

## 3. Verification, Docs, and Skill Closure

- [x] 3.1 Add/adjust tests for malicious host rejection, scan limit bounding, auto-scan responsiveness, transition conflicts, and startup migration gate behavior.
- [x] 3.2 Run full verification (`uv run pytest -q`, `openspec validate --type change hardening-runtime-ipc-core --strict`, `openspec validate --all --strict`).
- [x] 3.3 Update docs/trackers (`docs/current-task.md`, `docs/plan.md`, `docs/documentation.md`, `docs/implement.md`) for implemented hardening behavior.
- [x] 3.4 Skill Delta Review Gate: update existing skills (or add focused new skill) for migration-gated startup checks and concurrency troubleshooting, including verification commands and fallback paths.
