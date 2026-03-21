## Why

Agent task execution currently depends on a single successful LLM API call path. Transient provider failures such as rate limits, insufficient credit, and overloaded upstream services can cause agents to abandon useful work prematurely even when the failure would likely clear with time or after the next budget refill window.

## What Changes

- Add a kernel-owned retry policy for agent task execution when LLM/API failures are classified as transient or budget-recoverable.
- Introduce progressive backoff that starts with short delays and can extend to long delays such as hours or next-day retry windows.
- Persist retry state so scheduled retries survive process restarts and can be inspected by operators.
- Distinguish retryable failures (for example 429s, temporary provider overload, transport faults, temporarily exhausted credits) from terminal failures that should not loop.
- Surface retry status, next-attempt timing, and terminal exhaustion outcomes through canonical runtime observability paths.
- Keep workflow execution deterministic by ensuring one pending retry schedule per failed task attempt and by preventing tight retry loops.
- Define operator controls for inspecting, nudging, or cancelling deferred retries when needed.
- Out of scope: changing waterfall budget allocation policy itself, adding new provider integrations, or redesigning form/workflow semantics beyond retry-aware execution status.

## Capabilities

### New Capabilities
- `agent-task-retry-policy`: Progressive retry scheduling, persistence, classification, and operator visibility for agent task execution failures caused by transient or budget-recoverable LLM/API conditions.

### Modified Capabilities
- `agent-runtime-bootstrap`: Extend runtime requirements so task execution can defer and resume work across transient provider failures instead of failing immediately.
- `agentic-workflow-verification-surface`: Extend verification/reporting requirements so operators can inspect retry state, next-attempt timing, final retry exhaustion outcomes, and provider/model-level failure trends.

## Impact

- Likely affected code: runtime execution loop integration, usage/error capture, scheduler/daemon logic, persistence schema, runtime action endpoints, and operator helper scripts.
- Likely affected systems: Nanobot runtime integration, kernel runtime services, SQLite/Alembic migrations, and agent/operator SOP documentation.
- External dependencies: upstream LLM provider error taxonomy and LiteLLM/transport error shapes used for retry classification.
tation.
- External dependencies: upstream LLM provider error taxonomy and LiteLLM/transport error shapes used for retry classification.
