# OmniClaw Current Task

- active_change: `none`
- objective: change execution slice complete; prepare next active change (M07 planning).

## in_scope
- Confirm archive + validation records are complete for recent stabilization changes.
- Keep docs/skills aligned with implemented runtime + IPC behavior.
- Prepare next OpenSpec change selection for M07.

## out_of_scope
- New implementation work before next change is opened.

## tasks
- [x] Archive `hardening-runtime-ipc-core`.
- [x] Archive `ipc-invalid-feedback-and-dedupe`.
- [x] Sync specs via archive operations.
- [x] Update docs and skills for startup hardening and IPC dead-letter feedback flow.

## blockers
- None.

## acceptance_checks
- [x] `uv run pytest -q` passes.
- [x] `openspec validate --all --strict` passes.
- [x] No active open change remains.

## next_up
- Start M07 planning/proposal when approved.
