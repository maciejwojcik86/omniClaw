## ADDED Requirements

### Requirement: Runtime Bootstrap SHALL Launch from Canonical Nanobot Config and Workspace Paths
The kernel SHALL launch agent runtime using Nanobot and the node's canonical Nanobot config path `workspace/agents`.

#### Scenario: Gateway start resolves Nanobot runtime inputs
- **WHEN** runtime bootstrap is requested for an active provisioned agent
- **THEN** the kernel resolves the agent's Nanobot config path and workspace root from canonical node metadata
- **AND** the launch command passes those paths explicitly to Nanobot

### Requirement: Runtime Bootstrap SHALL Use Existing Nanobot Workspace Context Inputs
The runtime bootstrap workflow SHALL use existing Nanobot workspace context files and SHALL NOT introduce custom prompt-seed file creation in this change.

#### Scenario: Baseline files are provisioning-managed
- **WHEN** runtime bootstrap starts for a provisioned agent workspace
- **THEN** runtime launch proceeds without creating custom seed files
- **AND** relies on native Nanobot context files (for example `AGENTS.md`, `HEARTBEAT.md`, `SOUL.md`, `USER.md`, `TOOLS.md`)

## MODIFIED Requirements

### Requirement: Runtime Bootstrap SHALL Provide Gateway Control Actions
The kernel SHALL expose runtime control actions to start, stop, and inspect agent gateways for provisioned Nanobot agents.

#### Scenario: Gateway start requested
- **WHEN** gateway start is requested for a provisioned agent
- **THEN** the kernel launches the Nanobot gateway using that agent's canonical config/workspace inputs

#### Scenario: Gateway stop requested
- **WHEN** gateway stop is requested for a provisioned agent
- **THEN** the kernel stops the running Nanobot gateway process for that agent and reports updated state

#### Scenario: Gateway status requested
- **WHEN** gateway status is requested for a provisioned agent
- **THEN** the kernel reports current runtime state using the tracked Nanobot process metadata for that agent

### Requirement: Kernel DB SHALL Track Agent Gateway Runtime State
The kernel database SHALL track whether each deployed Nanobot-backed agent gateway is currently running and the latest enable/stop timestamps.

#### Scenario: Gateway transitions to running
- **WHEN** a gateway start action succeeds
- **THEN** node runtime state is updated to running with latest start timestamp

#### Scenario: Gateway transitions to stopped
- **WHEN** a gateway stop action succeeds
- **THEN** node runtime state is updated to stopped with latest stop timestamp

### Requirement: Gateway Control SHALL Validate Host and Use Safe Command Invocation
Gateway start actions MUST validate host input and execute Nanobot launch commands from sanitized arguments without shell-injection exposure.

#### Scenario: Valid host starts gateway
- **WHEN** a gateway start request uses a valid host value
- **THEN** runtime command execution proceeds and gateway state is updated

#### Scenario: Invalid host is rejected
- **WHEN** a gateway start request uses an invalid or unsafe host value
- **THEN** the request fails with HTTP 422 and no gateway process is started

## REMOVED Requirements

### Requirement: Runtime Bootstrap SHALL Launch Under Provisioned Linux User Context
**Reason**: AGENT runtime no longer depends on one dedicated Linux user per agent.

**Migration**: Store Nanobot config/workspace paths in canonical node metadata and launch Nanobot under the kernel user or an equivalent shared runtime user.

### Requirement: Runtime Bootstrap SHALL Use Existing Nullclaw Workspace Context Inputs
**Reason**: Nullclaw-specific workspace assumptions are replaced by Nanobot-native context files.

**Migration**: Provision Nanobot-native workspace assets and point runtime launch at the provisioned Nanobot workspace.
