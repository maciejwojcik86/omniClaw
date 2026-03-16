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

### Requirement: Agent Provisioning SHALL Use Company-Workspace Nanobot Agent Directories
The provisioning layer SHALL create AGENT nodes inside the selected company workspace under `<company-workspace-root>/agents/<agent_name>/` by default, with a sibling `config.json` and a nested Nanobot workspace subtree.

#### Scenario: Default AGENT paths are resolved
- **WHEN** an AGENT is provisioned without explicit path overrides
- **THEN** its config path is `<company-workspace-root>/agents/<agent_name>/config.json`
- **AND** its `workspace_root` is `<company-workspace-root>/agents/<agent_name>/workspace`

### Requirement: Provisioning SHALL Source Canonical Nanobot Files From The Selected Company Template Root
The provisioning layer SHALL source standard Nanobot workspace files from the selected company workspace template root `nanobot_workspace_templates`.

#### Scenario: Provisioning resolves template inputs
- **WHEN** the kernel scaffold or deploy helpers need baseline Nanobot workspace files
- **THEN** they load those files from `<company-workspace-root>/nanobot_workspace_templates`
- **AND** they MUST NOT depend on `<repo-root>/workspace/nanobot_workspace_templates`

### Requirement: Agent Provisioning SHALL Create External Instruction Template Roots In The Selected Company Workspace
Agent provisioning SHALL create and persist an external instruction template root for each provisioned AGENT under `<company-workspace-root>/nanobots_instructions/<agent_name>/`.

#### Scenario: Provisioned agent receives template root
- **WHEN** an AGENT is provisioned successfully
- **THEN** the kernel creates `<company-workspace-root>/nanobots_instructions/<agent_name>/`
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

### Requirement: Agent Provisioning SHALL Seed Default Loose Skills
Agent provisioning SHALL assign company-configured default loose skills to new AGENT nodes using the canonical master-skill assignment ledger.

#### Scenario: New agent receives default company skills
- **WHEN** an AGENT is provisioned and the selected company `config.json` declares default loose skills
- **THEN** the kernel records `DEFAULT` node-skill-assignment rows for each configured active loose skill
- **AND** excludes form-linked skills from that default list

### Requirement: Agent Provisioning SHALL Reconcile Initial Approved Skills
The provisioning flow SHALL reconcile the new AGENT workspace `skills/` directory after default and form-stage assignments are determined.

#### Scenario: Provisioned agent starts with approved skills only
- **WHEN** agent provisioning completes successfully
- **THEN** the kernel rebuilds the new agent workspace `skills/` directory from approved assignments
- **AND** the response includes the resulting skill-sync summary alongside the rendered instructions summary
