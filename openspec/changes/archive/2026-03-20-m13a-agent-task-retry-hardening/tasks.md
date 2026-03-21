## 1. Retry policy, persistence, and telemetry foundation

- [x] 1.1 Define canonical retry state model, failure classifications, and Alembic migration(s) for persisted retry records.
- [x] 1.2 Implement retry classification helpers for transient, budget-recoverable, and terminal LLM/API failures with representative fixture coverage.
- [x] 1.3 Implement deterministic progressive backoff scheduling logic, including long-delay windows for budget-recoverable conditions.
- [x] 1.4 Define and persist normalized failure telemetry fields for provider, model, failure class, and related agent/task context.

## 2. Runtime and scheduler integration

- [x] 2.1 Integrate runtime invocation paths so retryable failures record deferred retry state instead of failing immediately.
- [x] 2.2 Add a kernel-managed scheduler path that reloads due retry records, claims them safely, and resumes execution without duplicate runs.
- [x] 2.3 Extend runtime metadata/artifact reporting to include retry classification, scheduled next-attempt timing, terminal exhaustion outcomes, and provider/model failure dimensions.

## 3. Operator visibility and controls

- [x] 3.1 Add canonical runtime/reporting actions for listing retry state and inspecting pending or exhausted retries.
- [x] 3.2 Add canonical grouped reporting for provider/model failure trends over a time window.
- [x] 3.3 Add supported operator controls for retry-now and cancel flows, plus helper scripts under `scripts/`.
- [x] 3.4 Document the retry lifecycle, provider/model incident reporting, and operator recovery workflow in relevant docs and SOPs.

## 4. Validation and closure

- [x] 4.1 Add automated tests for short-backoff retries, long-delay budget retries, restart recovery, duplicate-claim protection, terminal classification, and provider/model aggregation.
- [x] 4.2 Run targeted verification plus `openspec validate --type change m13a-agent-task-retry-hardening --strict` and any relevant pytest coverage.
- [x] 4.3 Perform Skill Delta Review: update existing mirrored skills or create new `.codex/skills/*` and `skills/*` SOPs for retry operations, failure reporting, helper scripts, and verification commands.
