## Why

Recent audit findings identified high-risk issues in runtime command execution, IPC auto-scan scalability, transition concurrency safety, and startup schema-governance behavior. These weaknesses affect security and determinism now that form routing is always-on and the kernel is expected to run continuously.

## What Changes

- Harden runtime gateway start inputs and execution path to eliminate shell-command injection vectors.
- Bound IPC scan traversal strictly by requested limit and run background scan work off the event loop.
- Add deterministic optimistic concurrency controls for form transitions so conflicting writes fail cleanly.
- Enforce migration-first startup contract (no implicit schema creation at app startup).
- Refresh regression coverage for security/performance/concurrency scenarios and align docs/check outputs.

In scope:
- Runtime host validation and argument-safe gateway launch path.
- IPC scan-loop traversal and async execution hardening.
- Form transition conflict handling and unique event sequencing under concurrency.
- Startup migration revision checks with explicit operator guidance.
- Tests and docs updates required by these changes.

Out of scope:
- New operator-facing IPC error-feedback routing policy for invalid forms (handled in follow-up change).
- Skill distribution workflow redesign.
- Budgeting or side-effect execution milestones.

## Capabilities

### New Capabilities
- `runtime-ipc-hardening`: Security, concurrency, and startup-governance hardening requirements for runtime and IPC core paths.

### Modified Capabilities
- `agent-runtime-bootstrap`: Gateway start input validation and secure execution expectations are strengthened.
- `file-ipc-router`: Auto-scan traversal/latency behavior is tightened for bounded processing.
- `kernel-service-skeleton`: Startup behavior is tightened to require migration-aligned database state.
- `canonical-state-schema`: Form snapshot concurrency control metadata is added for deterministic transition writes.

## Impact

Affected code and systems:
- `src/omniclaw/runtime/*` for command construction and host validation.
- `src/omniclaw/ipc/*` and `src/omniclaw/app.py` for scan-loop behavior.
- `src/omniclaw/db/models.py`, `src/omniclaw/db/repository.py`, and Alembic migrations for optimistic locking.
- `src/omniclaw/db/session.py` / startup wiring for migration enforcement.
- `tests/test_runtime_actions.py`, `tests/test_ipc_actions.py`, and repository/service tests for new guarantees.
