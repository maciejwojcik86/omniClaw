Implement OmniClaw end-to-end using `docs/plan.md` as the execution source of truth.

Non-negotiable constraints

- Do not start milestone code before OpenSpec artifacts exist for that milestone.
- Keep exactly one active OpenSpec change at a time.
- Do not drift from milestone scope unless explicitly requested by the user.

Execution rules (strict)

- Read in this order before coding:
  1) `AGENTS.md`
  2) `docs/current-task.md`
  3) `docs/plan.md`
  4) Active `openspec/changes/<change-id>/tasks.md`

- For each milestone:
  1) Create change and author all artifacts (`proposal`, `specs`, `design`, `tasks`)
  2) Implement only scoped tasks
  3) Add/adjust tests for all changed behavior
  4) Run verification commands
  5) Update trackers/docs/repository map
  6) Validate and archive change

Verification requirements

After every milestone:
- `uv run pytest -q`
- `openspec validate --type change <change-id> --strict`

Regular checkpoint sweep:
- `openspec validate --all --strict`

Failure protocol

- If a bug is found:
  1) Add failing test first
  2) Fix implementation
  3) Confirm test passes
  4) Record short note in `docs/plan.md` Implementation Notes

Documentation requirements

- Keep `docs/documentation.md` accurate to current implementation.
- Do not document unreleased behavior as completed.
- Keep `docs/plan.md` milestone status and risk register updated.
- Keep `AGENTS.md` repository map updated when structure changes.

Completion criteria (for MVP gate)

- M03-M13 completed and archived in sequence.
- End-to-end autonomous budget request loop works reliably.
- Tests and strict OpenSpec validations pass.
- Documentation reflects real behavior and operator workflow.

Execution start instruction

- Resume from the active milestone listed in `docs/current-task.md`.
- If `docs/current-task.md` and `docs/plan.md` disagree, reconcile them before coding.

Current execution status

- Change `hardening-runtime-ipc-core` is complete and archived.
- Change `ipc-invalid-feedback-and-dedupe` is complete and archived.
- Current branch has no active open change.
- Next execution step: open M07 planning/proposal change when approved.
