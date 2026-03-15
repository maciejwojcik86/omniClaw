# linux-provisioning Specification

## Purpose
Define safe, testable Linux user/workspace provisioning primitives for OmniClaw agent onboarding, including mock/system adapters, deterministic workspace scaffolding, and manager-aware permission policy.
## Requirements
### Requirement: Provisioning Interface SHALL Support Mock and System Modes
The kernel provisioning layer SHALL provide interchangeable adapters for `mock` and `system` execution to support safe development and production rollout for HUMAN registration and AGENT workspace scaffolding.

#### Scenario: Test environment uses mock adapter
- **WHEN** provisioning is executed in tests
- **THEN** no real Linux users are created
- **AND** AGENT directory/config operations are captured deterministically

### Requirement: Workspace Scaffold SHALL Match OmniClaw Contract
Provisioning SHALL create the required workspace tree for a new agent.

#### Scenario: New agent is provisioned
- **WHEN** the provisioning workflow completes
- **THEN** required folders/files exist under the agent workspace, including Nanobot-native context assets (`AGENTS.md`, `HEARTBEAT.md`, `SOUL.md`, `USER.md`, `TOOLS.md`, `memory/`, `sessions/`) and OmniClaw operational folders (`inbox/new`, `outbox/send`, `outbox/drafts`, `outbox/archive`, `outbox/dead-letter`, `notes`, `drafts`, `skills`)

### Requirement: Agent Provisioning SHALL Use Repo-Local Nanobot Agent Directories
The provisioning layer SHALL create AGENT nodes inside repo-local Nanobot agent directories under `<repo-root>/workspace/agents/<agent_name>/` by default, with a sibling `config.json` and a nested Nanobot workspace subtree.

#### Scenario: Default AGENT paths are resolved
- **WHEN** an AGENT is provisioned without explicit path overrides
- **THEN** its config path is `<repo-root>/workspace/agents/<agent_name>/config.json`
- **AND** its `workspace_root` is `<repo-root>/workspace/agents/<agent_name>/workspace`

### Requirement: Provisioning SHALL Source Canonical Nanobot Files from the Named Template Root
The provisioning layer SHALL source standard Nanobot workspace files from the canonical repo path `workspace/nanobot_workspace_templates`.

#### Scenario: Provisioning resolves template inputs
- **WHEN** the kernel scaffold or deploy helpers need baseline Nanobot workspace files
- **THEN** they load those files from `workspace/nanobot_workspace_templates`
- **AND** they MUST NOT depend on the legacy pre-rename template root

### Requirement: Agent Provisioning SHALL Create External Instruction Template Roots
Agent provisioning SHALL create and persist an external instruction template root for each provisioned AGENT under `workspace/nanobots_instructions/<agent_name>/`.

#### Scenario: Provisioned agent receives template root
- **WHEN** an AGENT is provisioned successfully
- **THEN** the kernel creates `workspace/nanobots_instructions/<agent_name>/`
- **AND** persists that path on the AGENT node as its `instruction_template_root`

### Requirement: Agent Provisioning SHALL Render Initial AGENTS From External Template
The provisioning flow SHALL seed a default AGENTS template in the external template root and render the initial workspace `AGENTS.md` from that template.

#### Scenario: New agent starts with rendered AGENTS
- **WHEN** a new AGENT is provisioned without an existing instruction template
- **THEN** provisioning writes a default external `AGENTS.md` template
- **AND** renders the deployed workspace `AGENTS.md` from that external template before returning success

#### Scenario: Provisioning persists agent role label
- **WHEN** provisioning receives a `role_name` for the AGENT
- **THEN** the role label is stored in canonical node metadata and used by the initial render

