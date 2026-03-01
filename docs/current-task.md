# OmniClaw Current Task

- active_change: `m04-agent-runtime-bootstrap`
- objective: Build runtime bootstrap path to execute restricted Nullclaw runs for provisioned agents with seed-file initialization and run metadata capture.

## in_scope
- Create and author OpenSpec change artifacts for `m04-agent-runtime-bootstrap`.
- Implement runtime bootstrap service and endpoint for provisioned agent users.
- Implement seed-file initialization (`notes/TODO.md`, `persona_template.md`).
- Capture per-run metadata (timings, command, exit status, artifact paths).
- Add tests and a system smoke path for restricted runtime execution.

## out_of_scope
- File IPC router implementation (M05).
- Formal form state machine workflows (M06+).
- Budget sync/governance execution (M09+).

## tasks
- [x] Create OpenSpec change `m04-agent-runtime-bootstrap`.
- [x] Author OpenSpec artifacts (`proposal.md`, `specs/`, `design.md`, `tasks.md`).
- [ ] Implement runtime bootstrap module and endpoint.
- [ ] Add seed logic + metadata capture + tests.
- [ ] Run `uv run pytest -q` and strict OpenSpec validation for M04.

## blockers
- None.

## acceptance_checks
- [ ] Runtime bootstrap executes under provisioned Linux user context.
- [ ] Seed files are created when missing.
- [ ] Run metadata is captured for each execution.
- [ ] Restricted execution writes artifacts in drafts boundary.

## next_up
- Implement M04 tasks after Nullclaw command contract is confirmed.
