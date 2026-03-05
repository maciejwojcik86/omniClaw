## Why

With Linux provisioning complete, OmniClaw needs a runtime bootstrap layer that can safely launch a restricted Nullclaw process for an existing agent user and capture reproducible run metadata. This is required to prove agent execution works end-to-end before IPC/form workflows in M05+.

## What Changes

- Add runtime bootstrap service to control Nullclaw gateway start/stop as provisioned Linux users.
- Use existing native Nullclaw workspace context files; do not add M04-specific prompt seed generation.
- Add run metadata capture for each bootstrap execution (command, timings, exit code, output paths).
- Add DB runtime state tracking (gateway running + latest start/stop timestamps) per agent node.
- Add tests around command construction, safety checks, and metadata writes.
- Add HUMAN node registration path for existing kernel-running user with repo-local workspace.
- Enforce AGENT line-management contract (manager required; manager node can be HUMAN or AGENT).
- Add line-manager linking action for existing agent nodes.

## Capabilities

### New Capabilities
- `agent-runtime-bootstrap`: Launch and track restricted agent runtime executions against existing provisioned workspaces.
- `human-supervisor-baseline`: Register kernel runner as HUMAN node with workspace inside repo.
- `line-management-enforcement`: Ensure each AGENT has one manager link with hierarchy constraints.

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `src/omniclaw/runtime/*` (new module)
  - `src/omniclaw/app.py` (runtime endpoint wiring)
  - `src/omniclaw/config.py` (runtime config values)
  - `src/omniclaw/provisioning/*` (human registration + line-management actions)
  - `src/omniclaw/db/models.py` + migration (runtime state fields)
  - `tests/*runtime*`, `tests/*provisioning*`
- Affected scripts/docs:
  - runtime smoke script under `scripts/`
  - human/agent provisioning payload samples used for local operator runs
  - deploy skill workflow updates for line-management policy
  - docs updates for runtime bootstrap setup and verification
- Schema migration required for M04 runtime state tracking fields on `nodes`.
