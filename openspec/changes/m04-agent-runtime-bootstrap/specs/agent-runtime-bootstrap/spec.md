## ADDED Requirements

### Requirement: Runtime Bootstrap SHALL Launch Under Provisioned Linux User Context
The kernel SHALL provide a runtime bootstrap operation that executes the configured Nullclaw command under the target provisioned Linux user.

#### Scenario: Bootstrap request for active provisioned agent
- **WHEN** runtime bootstrap is requested for a provisioned agent user
- **THEN** the runtime command is executed under that Linux user context and not under the kernel process user

### Requirement: Bootstrap SHALL Seed Required Runtime Inputs
The runtime bootstrap workflow SHALL ensure required runtime seed files exist before execution.

#### Scenario: Seed files are missing
- **WHEN** runtime bootstrap starts and seed files are missing in the agent workspace
- **THEN** the workflow creates baseline `notes/TODO.md` and `persona_template.md` content under `~/.nullclaw/workspace` before launch

### Requirement: Runtime Bootstrap SHALL Capture Run Metadata
The runtime bootstrap workflow SHALL capture run metadata for every execution attempt.

#### Scenario: Runtime launch completes
- **WHEN** the runtime command exits (success or failure)
- **THEN** run metadata includes start/end timestamps, effective command, exit status, and output artifact paths

### Requirement: Runtime Bootstrap SHALL Enforce Drafts-Bound Output Policy
The runtime bootstrap workflow SHALL enforce M04 output boundaries for initial restricted execution.

#### Scenario: Runtime writes output
- **WHEN** runtime execution produces artifacts
- **THEN** artifacts are written within the agent workspace drafts boundary for this milestone
