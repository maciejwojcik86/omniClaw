## Context

IPC currently reports undelivered items but leaves invalid source files in sender pending queue. This causes repeated scans on the same invalid payload and no deterministic handoff artifact for correction. The codebase also duplicates node reference resolution and manager-link operations across modules.

## Goals / Non-Goals

**Goals:**
- Move invalid files out of pending queue in one pass.
- Emit structured error-feedback markdown to a deterministic inbox target.
- Preserve original invalid file in sender dead-letter location for audit/requeue.
- Provide explicit manual requeue helper script.
- Remove duplicated resolver/manager-link logic drift points.

**Non-Goals:**
- Automatic retries or autonomous correction.
- Policy-level authorization controls for requeue operator role.
- Additional DB tables for dead-letter queue management.

## Decisions

### 1) Dead-letter original + kernel-authored feedback artifact
- **Decision:** On validation/workflow failure, move source file to sender dead-letter path and generate a new feedback markdown artifact (do not forward original invalid file directly).
- **Rationale:** Keeps original evidence immutable while delivering actionable correction guidance.
- **Rejected alternative:** Keep original in pending and only report failure in API response. Rejected due to retry noise and poor operator ergonomics.

### 2) Feedback recipient routing with fallback
- **Decision:** If target can be resolved from frontmatter/context, deliver feedback to target inbox; otherwise deliver to sender inbox.
- **Rationale:** Implements requested policy while guaranteeing delivery path when target is invalid.
- **Rejected alternative:** Always route to sender only. Rejected because requested policy prioritizes target-inbox feedback where resolvable.

### 3) Structured YAML feedback contract
- **Decision:** Feedback frontmatter includes `error_code`, `error_message`, `invalid_field`, `original_source_path`, `original_target`, `original_stage`, `original_decision`.
- **Rationale:** Enables deterministic parsing and operator automation.
- **Rejected alternative:** Free-text feedback only. Rejected due to automation and triage limits.

### 4) Requeue is explicit script-only operation
- **Decision:** Add a helper script that moves selected dead-letter file(s) back to pending queue with overwrite-safe path handling.
- **Rationale:** Keeps retry intent explicit and auditable.
- **Rejected alternative:** Auto requeue on each scan after short delay. Rejected due to repeated invalid loops.

### 5) Dedupe by shared resolver and manager-link helpers
- **Decision:** Extract shared node-reference resolver used by forms and IPC; centralize manager-link create-if-missing logic in repository.
- **Rationale:** Reduces drift and improves consistent error semantics.
- **Rejected alternative:** Leave duplicate logic and rely on test parity. Rejected due to repeated maintenance risk.

## Risks / Trade-offs

- [Risk] Feedback routing could be noisy for frequent invalid drafts. -> Mitigation: deterministic dead-letter + explicit requeue keeps cycles controlled.
- [Risk] Target resolution fallback may surprise operators expecting sender-only feedback. -> Mitigation: expose recipient in response metadata.
- [Risk] Dedupe refactor might change edge-case error text. -> Mitigation: lock behavior with resolver-focused regression tests.

## Migration Plan

1. Implement new undelivered lifecycle and feedback writer in IPC service.
2. Update undelivered response payload contract.
3. Add requeue script in `scripts/ipc/` and usage docs.
4. Refactor shared resolver/manager-link helpers and update callers.
5. Add/adjust tests for malformed frontmatter, invalid target fallback, dead-letter replay.
6. Run full verification and strict OpenSpec validation.

Rollback strategy:
- Revert IPC dead-letter/feedback path and restore pending-retain behavior if feedback flow is rejected.
- Keep requeue script removal in same rollback commit.

## Open Questions

- Whether feedback message type should stay `MESSAGE` compatibility form or use dedicated `form_type` in future.
- Whether to persist feedback artifact paths in `forms_ledger` for failed deliveries in future change.
