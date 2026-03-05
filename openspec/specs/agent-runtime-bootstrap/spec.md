# agent-runtime-bootstrap Specification

## Purpose
Provide canonical runtime bootstrap and gateway lifecycle control for deployed Nullclaw agents, including auditable metadata capture, canonical DB runtime-state tracking, and baseline human-supervisor hierarchy setup needed for subsequent workflow-routing milestones.
## Requirements
### Requirement: Runtime Bootstrap SHALL Launch Under Provisioned Linux User Context
The kernel SHALL provide a runtime bootstrap operation that executes the configured Nullclaw command under the target provisioned Linux user.

#### Scenario: Bootstrap request for active provisioned agent
- **WHEN** runtime bootstrap is requested for a provisioned agent user
- **THEN** the runtime command is executed under that Linux user context and not under the kernel process user

### Requirement: Runtime Bootstrap SHALL Provide Gateway Control Actions
The kernel SHALL expose runtime control actions to start and stop agent gateways for provisioned agent users.

#### Scenario: Gateway start requested
- **WHEN** gateway start is requested for a provisioned agent
- **THEN** the kernel launches Nullclaw gateway under that agent Linux user context

#### Scenario: Gateway stop requested
- **WHEN** gateway stop is requested for a provisioned agent
- **THEN** the kernel stops the running gateway process for that agent and reports updated state

### Requirement: Runtime Bootstrap SHALL Use Existing Nullclaw Workspace Context Inputs
The runtime bootstrap workflow SHALL use existing Nullclaw workspace context files and SHALL NOT introduce custom prompt-seed file creation in M04.

#### Scenario: Baseline files are provisioning-managed
- **WHEN** runtime bootstrap starts for a provisioned agent workspace
- **THEN** runtime launch proceeds without creating custom seed files and relies on native Nullclaw context files (for example `AGENTS.md`, `SOUL.md`, `USER.md`)

### Requirement: Runtime Bootstrap SHALL Capture Run Metadata
The runtime bootstrap workflow SHALL capture run metadata for every execution attempt.

#### Scenario: Runtime launch completes
- **WHEN** the runtime command exits (success or failure)
- **THEN** run metadata includes start/end timestamps, effective command, exit status, and output artifact paths

### Requirement: Kernel DB SHALL Track Agent Gateway Runtime State
The kernel database SHALL track whether each deployed agent gateway is currently running and the latest enable/stop timestamps.

#### Scenario: Gateway transitions to running
- **WHEN** a gateway start action succeeds
- **THEN** node runtime state is updated to running with latest start timestamp

#### Scenario: Gateway transitions to stopped
- **WHEN** a gateway stop action succeeds
- **THEN** node runtime state is updated to stopped with latest stop timestamp

### Requirement: Runtime Bootstrap SHALL Enforce Drafts-Bound Output Policy
The runtime bootstrap workflow SHALL enforce M04 output boundaries for initial restricted execution.

#### Scenario: Runtime writes output
- **WHEN** runtime execution produces artifacts
- **THEN** artifacts are written within the agent workspace drafts boundary for this milestone

### Requirement: Kernel SHALL Support Human Supervisor Node Registration for Kernel Runner
The kernel SHALL support registering an existing Linux user (the kernel runner) as a HUMAN node with a repo-local workspace for formal workflow participation.

#### Scenario: Register existing kernel-running user as HUMAN node
- **WHEN** a registration request is submitted for an existing Linux user (for example `macos`)
- **THEN** the kernel upserts a HUMAN node with linux username, repo-local workspace path, and runtime/config metadata

#### Scenario: Human workspace uses repo-local structure
- **WHEN** no explicit human workspace root is provided
- **THEN** the kernel defaults workspace to `<repo-root>/workspace/<linux-username>` and scaffolds the standard workspace structure

### Requirement: Agent Provisioning SHALL Enforce Single Line Management
The kernel SHALL enforce that each AGENT node has exactly one line manager node (HUMAN or AGENT).

#### Scenario: Agent provisioning without manager reference is rejected
- **WHEN** `provision_agent` request omits both `manager_node_id` and `manager_node_name`
- **THEN** the request is rejected with validation error

#### Scenario: Agent manager must exist and be manager-capable node type
- **WHEN** manager reference resolves to missing node or unsupported manager type
- **THEN** the request is rejected

#### Scenario: Existing agent linked to manager
- **WHEN** `set_line_manager` action is called for an existing AGENT and manager node
- **THEN** the hierarchy relation is created if missing and duplicate/conflicting manager links are prevented

### Requirement: App Setup SHALL Bootstrap One Human Supervisor Baseline
At application setup, the kernel-running Linux user SHALL be registerable as a HUMAN supervisor node once, with repo-local workspace and top-agent linkage.

#### Scenario: One-time human supervisor bootstrap
- **WHEN** setup initializes HUMAN node for kernel user (for example `macos`)
- **THEN** node registration is idempotent and workspace scaffold exists under repo root

#### Scenario: Top agent linked to human supervisor
- **WHEN** top-level AGENT (for example `Director_01`) is linked to the human supervisor
- **THEN** hierarchy reflects HUMAN -> top AGENT baseline for downstream delegated management

### Requirement: Gateway Control SHALL Validate Host and Use Safe Command Invocation
Gateway start actions MUST validate host input and execute launch commands without shell-injection exposure.

#### Scenario: Valid host starts gateway
- **WHEN** a gateway start request uses a valid host value
- **THEN** runtime command execution proceeds and gateway state is updated

#### Scenario: Invalid host is rejected
- **WHEN** a gateway start request uses an invalid or unsafe host value
- **THEN** the request fails with HTTP 422 and no gateway process is started

