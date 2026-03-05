## Context
> Legacy archive note: this historical design document keeps original M05 wording (including "transition" terms) for audit fidelity.

M04 delivered provisioning + runtime control but no inter-node communication bus. M05 must introduce deterministic file IPC so HUMAN and AGENT nodes can exchange formal markdown messages through canonical kernel routing, not ad hoc direct file writes.

Current constraints from implemented codebase:
- Workspaces already exist per node with inbox/outbox boundaries.
- Canonical DB and repository layer are available, but forms routing metadata is not yet persisted beyond baseline fields.
- No IPC module exists yet.

User direction for M05 baseline:
- Treat initial form as an email-like `MESSAGE`.
- Minimal frontmatter fields only: destination node name, subject, type (`MESSAGE`), and name.
- Kernel tracks additional sender/time/lifecycle metadata in DB (not only what appears in frontmatter).
- Agent SOP must use drafts-first authoring and then submit to send queue for daemon routing.

## Goals / Non-Goals

**Goals:**
- Implement deterministic router scan/routing for markdown `MESSAGE` forms.
- Enforce hierarchy-based permission checks before delivery.
- Persist full message lifecycle records in canonical DB, including kernel-derived sender/timestamps/paths.
- Support deterministic file outcomes for successful archive and failed dead-letter flows.
- Add integration tests for success path SLA and permission/validation failures.
- Deliver two skills:
  - Developer-facing IPC architecture/extensibility skill.
  - Agent-facing message authoring/sending skill with template.

**Non-Goals:**
- Full form workflow transition engine with rich approval states (M06).
- Action executors for approved operational forms (M07).
- Budget transfer execution embedded in message routing.
- Context-injector and AGENTS rendering logic changes.

## Decisions

### 1) Initial Form Contract
- **Chosen for M05:** Minimal YAML frontmatter contract for queue-ready files:
  - `type: MESSAGE`
  - `target: <node-name>`
  - `subject: <short subject>`
  - `name: <file-name>`
- **Rationale:** Keeps first bus primitive simple while still formal and machine-validatable.
- **Rejected alternative:** Rich schema with sender/status/body metadata in frontmatter; rejected because kernel should derive authoritative sender/state from canonical context and filesystem location.

### 2) Sender Identity Source of Truth
- **Chosen for M05:** Infer sender from source workspace mapping in DB; do not trust sender in frontmatter.
- **Rationale:** Prevents spoofing and keeps identity canonical.
- **Rejected alternative:** Require `sender` in frontmatter and trust it if present.

### 3) Routing Permission Policy
- **Chosen for M05:** Allow routes only between directly linked manager/subordinate pairs in either direction.
- **Rationale:** Uses existing single-line-manager hierarchy and delivers strict, auditable minimum permissions.
- **Rejected alternative:** Allow arbitrary ancestry traversal or org-wide broadcast in M05.

### 4) Outbox Lifecycle Paths
- **Chosen for M05:** Keep agent drafting in `outbox/drafts`, submit to router send queue, then transition to archive/dead-letter outcomes.
  - Send queue baseline: `outbox/sent` (user-requested operator flow)
  - Compatibility read path: also accept `outbox/pending` during transition
  - Success terminal path: `outbox/archive`
  - Failure path: `outbox/dead-letter`
- **Rationale:** Matches requested user/agent SOP while preserving compatibility with earlier workspace scaffolding.
- **Rejected alternative:** Only `outbox/pending` queue with no archive tier.

### 5) Canonical DB Tracking Model
- **Chosen for M05:** Extend `forms_ledger` with message routing metadata (sender, target, subject, filesystem paths, lifecycle timestamps, failure reason).
- **Rationale:** Reuses canonical form ledger while adding required observability for message audit and future form-type expansion.
- **Rejected alternative:** Create a separate M05-only `messages` table, which would split canonical form state before M06.

### 6) Router Execution Control
- **Chosen for M05:** Implement deterministic scan entrypoint via kernel action endpoint (scan-once), with reusable loop helper for daemon operation.
- **Rationale:** Keeps tests deterministic and gives operators explicit control while enabling later always-on daemonization.
- **Rejected alternative:** Only background loop daemon with no direct trigger path.

## Risks / Trade-offs

- [Risk] `outbox/sent` as send queue may confuse semantics relative to historic naming. -> Mitigation: document explicit lifecycle and normalize with archive/dead-letter paths.
- [Risk] Direct-link permission policy may be too restrictive for real workflows. -> Mitigation: keep policy module isolated and expandable in later milestone.
- [Risk] Frontmatter parser edge cases could cause false dead-letter outcomes. -> Mitigation: strict parser tests and explicit failure reason capture.
- [Risk] Schema changes in `forms_ledger` before M06 might require later adjustment. -> Mitigation: add additive columns only and avoid irreversible coupling to executor logic.

## Migration Plan

1. Add M05 schema migration for message lifecycle metadata fields and any enum additions (`MESSAGE` and routing statuses).
2. Add IPC router module with scan-once service and routing/permission/metadata write paths.
3. Add kernel endpoint wiring for deterministic router scan action.
4. Add/adjust workspace scaffold directories for drafts/archive/dead-letter compatibility.
5. Add integration tests and run full validation gates.
6. Update docs and add two mandatory M05 skills.

Rollback strategy:
- Disable/avoid invoking IPC endpoint path.
- Keep migration rollback available via Alembic downgrade.
- Preserve existing provisioning/runtime features untouched.

## Open Questions

- Whether routed receiver-side files should be copied as-is or wrapped with kernel-delivery envelope metadata in M05.
- Whether sender-side archive should remain in place indefinitely or support retention pruning in later milestones.
- Whether future non-`MESSAGE` forms will share the same queue paths or branch by type-specific queues.
