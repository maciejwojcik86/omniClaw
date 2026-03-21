## Context

OmniClaw can start agent runtimes and trigger prompt execution, but the current execution path treats upstream LLM/API failures mostly as immediate run failures. In practice, provider-side conditions such as HTTP 429 rate limiting, overloaded backends, transient transport errors, and temporarily exhausted account credits can often recover without human intervention if the system waits and retries.

This change crosses runtime integration, persistence, observability, and operator control surfaces. It also affects stateful behavior because deferred retries must survive kernel or host restarts and must not duplicate work or create retry storms.

## Goals / Non-Goals

**Goals:**
- Add a canonical retry policy for agent task execution failures caused by transient or budget-recoverable upstream LLM/API conditions.
- Support progressive backoff that can expand from short waits to long waits measured in hours or next-day retry windows.
- Persist retry state so scheduled work survives process restarts and can be inspected or controlled through canonical operator surfaces.
- Keep retry behavior deterministic, bounded, and auditable.
- Preserve a clear distinction between retryable failures and terminal failures.

**Non-Goals:**
- Rework the waterfall budget engine or automatically top up budgets as part of this change.
- Add new external model providers or redesign LiteLLM itself.
- Redesign form lifecycle semantics beyond exposing retry-aware execution state.
- Guarantee successful completion for permanently invalid prompts, revoked credentials, or unsupported-model errors.

## Decisions

### Decision: Introduce a persisted retry ledger for runtime task attempts
The kernel will persist retry state for each failed task execution in canonical storage, including task identity, failure classification, attempt count, next attempt time, last error summary, and terminal-exhaustion outcome.

Rationale:
- Deferred retries must survive restarts and host interruptions.
- Operators need a canonical inspection path instead of parsing runtime logs.
- Persistence enables deterministic de-duplication so one task has at most one active pending retry schedule.

Rejected alternative:
- Keep retry state only in process memory. This was rejected because long backoff windows and restarts would silently drop scheduled work.

### Decision: Classify failures into retryable transient, retryable budget-recoverable, and terminal buckets
Runtime integration will normalize upstream provider/LiteLLM errors into coarse policy classes. Retryable transient covers rate limits, overload, upstream 5xx, and transport faults. Retryable budget-recoverable covers temporarily exhausted credits or quota conditions that may resolve after the next refill cycle. Terminal covers malformed requests, invalid auth, unsupported models, and policy-rejected work.

Rationale:
- The backoff profile should depend on the type of failure, not only the raw exception string.
- Coarse classes keep policy stable even when provider-specific wording changes.

Rejected alternative:
- Retry every non-2xx error with one generic policy. This was rejected because invalid credentials or malformed requests would loop uselessly.

### Decision: Use a progressive backoff schedule with capped short-term retries and long-horizon deferral
The policy will begin with short delays for likely transient faults and then widen delays progressively. Budget-recoverable failures may jump directly to longer windows aligned with company budget reset time or the next calendar day when classification indicates immediate retry is unlikely to help.

Rationale:
- Fast recovery is desirable for temporary overloads.
- Long waits are necessary for exhausted-credit situations where the only realistic recovery path is later budget replenishment.
- A deterministic schedule is easier to test and explain than free-form exponential retry.

Rejected alternative:
- Fixed exponential backoff only. This was rejected because it does not model budget-reset realities well and can still waste many attempts during prolonged exhaustion.

### Decision: Drive retries through a kernel-managed scheduler loop instead of letting individual runtime processes sleep for hours
Failed work will be rescheduled by the kernel and re-enqueued when due, rather than having one runtime process hold open a long sleep.

Rationale:
- Long-lived sleeping processes are fragile, harder to inspect, and waste resources.
- Kernel scheduling provides one canonical place for dedupe, cancellation, and observability.

Rejected alternative:
- Let Nanobot or subprocess callers sleep until retry time. This was rejected because it complicates restart recovery and operator visibility.

### Decision: Expose operator controls and reporting through existing canonical runtime/reporting surfaces
Operators will be able to list pending retries, inspect the last failure classification and next-attempt time, trigger an immediate retry, or cancel a schedule through supported kernel actions and helper scripts.

Rationale:
- This aligns with the repo rule that autonomous/operator workflows should use canonical endpoints or scripts.
- It keeps retry state auditable and avoids repo-local log scraping.

Rejected alternative:
- Require operators to inspect SQLite rows or raw logs. This was rejected because it is non-canonical and unsuitable for future agents.

### Decision: Track failure telemetry at provider/model granularity in addition to agent/task granularity
The system will record normalized failure telemetry with provider, model, error class, and time-window dimensions so operators can detect shared incidents affecting many agents that use the same upstream model or provider.

Rationale:
- Many agents can fail for the same upstream reason even when their virtual keys and task contexts differ.
- Provider/model aggregation helps distinguish "one broken agent" from "Gemini/OpenAI/Anthropic model X is currently degraded".
- This supports future rate-shaping or provider failover decisions without requiring those features in this change.

Rejected alternative:
- Keep only per-agent retry rows and derive provider incidents manually from logs. This was rejected because it makes shared-outage detection slow and non-canonical.

## Risks / Trade-offs

- [Misclassified provider errors] → Mitigation: normalize provider error parsing behind a dedicated classifier with regression fixtures for known LiteLLM/provider shapes.
- [Duplicate execution after restart or scheduler races] → Mitigation: persist one active retry row per task attempt lineage and use atomic claim/update transitions when due work is dequeued.
- [Excessive delayed backlog growth] → Mitigation: cap attempts, surface backlog metrics, and allow operator cancellation/inspection of stale retries.
- [Retries mask permanent configuration problems] → Mitigation: treat invalid auth, invalid model, and malformed request failures as terminal and expose the classification reason.
- [Long delays reduce responsiveness] → Mitigation: keep short retries for transient overloads and provide manual “retry now” controls for operators.

## Migration Plan

1. Add canonical persistence for retry state and any supporting enums/columns through Alembic.
2. Add runtime error-classification and retry-schedule computation helpers with unit coverage for representative provider failures.
3. Integrate runtime invocation paths so retryable failures persist deferred work rather than finishing immediately as terminal failures.
4. Add scheduler processing, runtime/reporting actions, and helper scripts for inspection/retry/cancel flows.
5. Validate with targeted tests for short retry, long retry, restart recovery, terminal classification, and operator visibility.

Rollback:
- Disable scheduler processing for the new retry queue and treat pending items as inert records.
- Revert the runtime integration to immediate-failure behavior if needed while preserving rows for forensic inspection.

## Open Questions

- What is the canonical task identity for de-duplicating retries across all invocation paths: runtime run id, session key + prompt hash, or a workflow-owned execution id?
- Should budget-recoverable retry timing align strictly to configured company `reset_time_utc`, or should the initial implementation allow a simpler next-day fallback when no budget window is resolvable?
- Which operator endpoint namespace is the best fit for retry controls: extend runtime actions, extend usage/reporting actions, or create a dedicated retry action surface?
