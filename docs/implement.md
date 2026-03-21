Active implementation change: `m13a-agent-task-retry-hardening`

Implementation focus

1. Add canonical persistence for retry schedules and provider/model failure telemetry.
2. Implement retry classification and progressive backoff helpers before wiring runtime execution paths.
3. Keep the first implementation slice narrowly scoped to tasks 1.1-1.4, with runtime/scheduler integration deferred to the next slice.

Status

- OpenSpec artifacts for `m13a-agent-task-retry-hardening` are authored and strictly validated.
- The repo currently has usage tracking in `agent_llm_calls`, but no canonical persistence for retry state or provider/model failure events.
- Runtime prompt invocation still fails immediately on upstream errors; deferred retries are not yet implemented.

Planned verification for current slice

- Alembic head upgrade includes new retry/failure telemetry tables and columns.
- Repository tests cover persistence of retry records and grouped failure telemetry queries.
- Retry policy tests cover transient classification, budget-recoverable classification, terminal classification, and deterministic next-attempt scheduling.

Notes

- Prefer raw canonical event persistence first; reporting and scheduler processing can build on that state in later tasks.
- Budget-recoverable scheduling should align to configured reset windows when available, with deterministic next-day fallback otherwise.
