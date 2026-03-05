## 1. Schema and Contracts
> Legacy archive note: this archived task list preserves original M05 language, including filesystem "transitions" terminology.

- [x] 1.1 Add `MESSAGE` form type and message-routing lifecycle status coverage in DB enums/schemas.
- [x] 1.2 Create Alembic migration to extend `forms_ledger` with sender/target/subject/path/timestamp/failure metadata fields required for M05 tracking.
- [x] 1.3 Add repository operations for creating/updating message lifecycle records from router execution.

## 2. IPC Router Core

- [x] 2.1 Implement `src/omniclaw/ipc/` module with markdown frontmatter parser and validation for minimal `MESSAGE` contract.
- [x] 2.2 Implement workspace scan + sender resolution + hierarchy permission checks for routable nodes.
- [x] 2.3 Implement deterministic filesystem transitions for send queue, inbox delivery, archive success, and dead-letter failure outcomes.
- [x] 2.4 Implement router scan summary payload with counts and per-item reason codes.

## 3. Kernel Wiring and Workspace Compatibility

- [x] 3.1 Add kernel endpoint/action wiring for deterministic IPC scan execution.
- [x] 3.2 Update workspace scaffold contract for `outbox/drafts`, `outbox/archive`, and `outbox/dead-letter` while preserving compatibility with existing `outbox/pending`/`outbox/sent` paths.
- [x] 3.3 Add runtime-safe configuration defaults for router polling/scan behavior and queue path selection.

## 4. Verification and Regression Coverage

- [x] 4.1 Add integration test: authorized A->B message route succeeds within target routing window.
- [x] 4.2 Add integration test: unauthorized route is dead-lettered with persisted failure reason.
- [x] 4.3 Add integration test: malformed frontmatter is dead-lettered and does not deliver.
- [x] 4.4 Run `uv run pytest -q` and `openspec validate --type change m05-file-ipc-router --strict`.

## 5. Documentation and Skill Closure

- [x] 5.1 Update `docs/documentation.md`, `docs/current-task.md`, `docs/plan.md`, and `docs/implement.md` with M05 IPC behavior and status.
- [x] 5.2 Create/update developer-facing skill documenting IPC architecture, lifecycle model, permission policy, and how to add new form types.
- [x] 5.3 Create agent-facing skill documenting how to draft and submit `MESSAGE` files (template, field rules, draft-review-submit SOP).
- [x] 5.4 Run OpenSpec Skill Review Gate and confirm reusable commands/scripts are captured in skill docs.
