## ADDED Requirements

### Requirement: Provisioning SHALL Source Canonical Nanobot Files from the Named Template Root
The provisioning layer SHALL source standard Nanobot workspace files from the canonical repo path `workspace/nanobot_workspace_templates`.

#### Scenario: Provisioning resolves template inputs
- **WHEN** the kernel scaffold or deploy helpers need baseline Nanobot workspace files
- **THEN** they load those files from `workspace/nanobot_workspace_templates`
- **AND** they MUST NOT depend on `workspace/agent_templates`

## MODIFIED Requirements

### Requirement: Workspace Scaffold SHALL Match OmniClaw Contract
Provisioning SHALL create the required workspace tree for a new agent.

#### Scenario: New agent is provisioned
- **WHEN** the provisioning workflow completes
- **THEN** required folders/files exist under the agent workspace, including Nanobot-native context assets (`AGENTS.md`, `HEARTBEAT.md`, `SOUL.md`, `USER.md`, `TOOLS.md`, `memory/`, `sessions/`) and OmniClaw operational folders (`inbox/new`, `outbox/send`, `outbox/drafts`, `outbox/archive`, `outbox/dead-letter`, `notes`, `drafts`, `skills`)
