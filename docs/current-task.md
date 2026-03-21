# OmniClaw Current Task

- active_change: `none`
- objective: Select the next change after closing retry hardening.

## last_completed_change
- change: `m13a-agent-task-retry-hardening`
- archived_as: `openspec/changes/archive/2026-03-20-m13a-agent-task-retry-hardening`
- closure_notes:
  - Added persisted retry state in `agent_task_retries` and provider/model failure telemetry in `agent_llm_failure_events`.
  - Implemented retry classification (`transient`, `budget_recoverable`, `terminal`) with progressive backoff and long-delay retry windows.
  - Added kernel-managed retry scheduling, canonical reporting endpoints, operator retry/cancel controls, and helper scripts.
  - Fixed Alembic default DB resolution so CLI migrations follow the registry-backed company workspace instead of stale repo-local paths.

## next_focus
- No active change selected.
- Recommended next change: canonical company bootstrap/init flow for multi-company setup.

## blockers
- None for the archived retry-hardening change.

## current_status
- `m13a-agent-task-retry-hardening` is archived after strict validation and targeted verification (`31 passed`).
- Canonical specs were updated during archive.
- Retry lifecycle, provider/model incident reporting, and operator recovery workflow are now documented in `docs/documentation.md`.

## next_up
- Open the follow-up company bootstrap/init change for multi-company setup.
- Keep using the registry-backed per-company DB model as the canonical architecture.
- Investigate unrelated dirty worktree items separately from the archived M13a change.
