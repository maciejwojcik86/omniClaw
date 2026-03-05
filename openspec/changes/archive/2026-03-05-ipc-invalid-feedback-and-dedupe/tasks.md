## 1. Invalid-Form Lifecycle and Feedback Routing

- [x] 1.1 Update IPC undelivered handling to move invalid source files from pending queue to sender dead-letter path.
- [x] 1.2 Add kernel-authored feedback artifact generation with structured YAML error fields.
- [x] 1.3 Implement feedback delivery routing: resolved target inbox first, sender inbox fallback when target is unresolved.
- [x] 1.4 Extend IPC undelivered response payload with `dead_letter_path` and `feedback_path` metadata.

## 2. Requeue Tooling and Dedupe Refactor

- [x] 2.1 Add `scripts/ipc/requeue_dead_letter.sh` for explicit dead-letter-to-pending replay with collision-safe naming.
- [x] 2.2 Consolidate node-reference resolver logic shared by IPC/forms into a common helper path.
- [x] 2.3 Consolidate duplicate manager-link logic in repository into single shared flow.

## 3. Verification, Docs, and Skill Closure

- [x] 3.1 Add/adjust tests for malformed frontmatter dead-lettering, target resolution fallback, response metadata, and requeue flow.
- [x] 3.2 Run full verification (`uv run pytest -q`, `openspec validate --type change ipc-invalid-feedback-and-dedupe --strict`, `openspec validate --all --strict`).
- [x] 3.3 Update docs/trackers (`docs/current-task.md`, `docs/plan.md`, `docs/documentation.md`, `docs/implement.md`) for dead-letter + feedback behavior.
- [x] 3.4 Skill Delta Review Gate: update IPC/router and operator skills with dead-letter feedback and requeue SOPs.
