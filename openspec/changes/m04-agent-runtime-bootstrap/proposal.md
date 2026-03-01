## Why

With Linux provisioning complete, OmniClaw needs a runtime bootstrap layer that can safely launch a restricted Nullclaw process for an existing agent user and capture reproducible run metadata. This is required to prove agent execution works end-to-end before IPC/form workflows in M05+.

## What Changes

- Add runtime bootstrap service to launch Nullclaw commands as provisioned Linux users.
- Add bootstrap seed logic for minimal runtime inputs in `~/.nullclaw/workspace` (e.g., `notes/TODO.md`, `persona_template.md`) when missing.
- Add run metadata capture for each bootstrap execution (command, timings, exit code, output paths).
- Add tests around command construction, safety checks, and metadata writes.

## Capabilities

### New Capabilities
- `agent-runtime-bootstrap`: Launch and track restricted agent runtime executions against existing provisioned workspaces.

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `src/omniclaw/runtime/*` (new module)
  - `src/omniclaw/app.py` (runtime endpoint wiring)
  - `src/omniclaw/config.py` (runtime config values)
  - `tests/*runtime*`
- Affected scripts/docs:
  - runtime smoke script under `scripts/`
  - docs updates for runtime bootstrap setup and verification
- No required schema migration planned for M04; run metadata will be captured in filesystem artifacts for this milestone.
