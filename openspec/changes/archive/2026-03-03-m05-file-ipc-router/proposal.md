## Why
> Legacy archive note: this historical proposal preserves original M05 terminology, including "transition" wording that predated the decision-term standard.

M05 establishes the first production communication bus for OmniClaw: file-based message routing between HUMAN and AGENT workspaces with canonical DB tracking. This is required before form-state automation milestones because kernel workflows depend on deterministic inbox/outbox delivery, permission enforcement, and auditable message lifecycle state.

## What Changes

- Add a file IPC router capability that scans workspace outboxes and routes Markdown messages to destination inboxes.
- Introduce a minimal `MESSAGE` frontmatter contract for initial email-like communication:
  - `type: MESSAGE`
  - `target: <node-name>`
  - `subject: <short-subject>`
  - `name: <message-file-name>`
- Enforce sender/receiver permission checks using canonical hierarchy relationships.
- Persist routed message lifecycle in the canonical DB with more kernel-tracked metadata than the frontmatter (for example sender, routing timestamps, source/destination paths, and routing status).
- Define deterministic filesystem lifecycle from send queue to archival/dead-letter handling.
- Add API/daemon-facing router controls to execute deterministic scan/routing cycles.
- Add integration tests proving A->B message routing within the target window and permission/dead-letter behavior.
- Add two skills as mandatory closure work:
  - Developer skill documenting router architecture and extensibility for future form types.
  - Agent-facing skill documenting how to draft and submit a `MESSAGE` form with template examples.

In scope:
- M05 file IPC router only (message parsing, permission checks, filesystem routing, DB tracking, and tests).
- Initial `MESSAGE` form type and lifecycle states needed for routing and archive/dead-letter outcomes.
- Skills and operator/agent SOP documentation for message workflow.

Out of scope:
- Full multi-state approval workflow engine and transition governance (M06+).
- Approval-triggered side effects like provisioning/template mutation (M07+).
- Budget transfer logic in message frontmatter (deferred).
- Context injection rendering behavior (M08+).

## Capabilities

### New Capabilities
- `file-ipc-router`: Scan outbound message queue files, validate minimal frontmatter, enforce routing permissions, route files to inboxes, and track message lifecycle in canonical DB with auditable metadata.

### Modified Capabilities
- `canonical-state-schema`: Extend canonical form-type/status coverage to include message routing lifecycle states and persisted sender/recipient routing metadata required by M05.

## Impact

- Affected code:
  - `src/omniclaw/ipc/*` (new router service, parsing, permission policy, lifecycle tracking)
  - `src/omniclaw/app.py` (router action endpoint wiring)
  - `src/omniclaw/db/models.py` and `src/omniclaw/db/repository.py` (message lifecycle persistence fields/operations)
  - `src/omniclaw/db/enums.py` (form type/status coverage update)
  - `src/omniclaw/provisioning/scaffold.py` (outbox draft/archive/dead-letter directory contract if needed)
  - `tests/*ipc*`, `tests/test_schema_repository.py` (routing + schema coverage)
- Affected API surface:
  - New IPC router action endpoint (or equivalent service control) for deterministic scan execution.
- Stateful impact:
  - Alembic migration for form lifecycle metadata/schema updates.
- Documentation/skills:
  - `docs/documentation.md`, `docs/plan.md`, `docs/current-task.md`, `docs/implement.md`
  - New/updated skills under `.codex/skills/` for developer and agent message workflows.
