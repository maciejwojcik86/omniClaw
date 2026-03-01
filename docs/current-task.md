# OmniClaw Current Task

- active_change: `m03-linux-provisioning` (archived as `2026-03-01-m03-linux-provisioning`)
- objective: M03 complete. Linux provisioning is operational in both mock and system modes with endpoint-driven privileged execution.

## in_scope
- Create and author OpenSpec change artifacts for `m03-linux-provisioning`.
- Implement provisioning interface with mock and system adapters.
- Implement workspace tree scaffolding and ownership/group permission logic.
- Add tests for mock adapter behavior and provisioning metadata updates.
- Capture validated provisioning steps as reusable project-local skills.

## out_of_scope
- Nullclaw runtime bootstrap service wrappers (M04).
- IPC file router implementation (M05).
- Formal form state machine workflows (M06+).

## tasks
- [x] Create OpenSpec change `m03-linux-provisioning`.
- [x] Author OpenSpec artifacts (`proposal.md`, `specs/`, `design.md`, `tasks.md`).
- [x] Define modular skill-first provisioning workflow and initial helper scripts.
- [x] Implement provisioning adapters and workspace scaffold logic.
- [x] Add mock-first tests and manual system verification script.
- [x] Run `uv run pytest -q` and strict OpenSpec validation for M03.
- [x] Run `openspec validate --all --strict`.
- [x] Archive `m03-linux-provisioning`.

## blockers
- None.

## acceptance_checks
- [x] Provisioning interface supports both `mock` and `system` modes.
- [x] Workspace tree and permissions are created as expected.
- [x] OpenSpec strict validation passes for `m03-linux-provisioning`.
- [x] Real Linux user/workspace provisioning verified via `/v1/provisioning/actions` in `system` mode.

## next_up
- Create OpenSpec change for M04 (`m04-agent-runtime-bootstrap`) and begin runtime bootstrap implementation.
