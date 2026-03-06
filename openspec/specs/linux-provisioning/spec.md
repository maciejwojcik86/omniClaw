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
- **THEN** required folders/files exist under the agent workspace, including Nanobot-native context assets (`AGENTS.md`, `HEARTBEAT.md`, `SOUL.md`, `USER.md`, `TOOLS.md`, `memory/`, `sessions/`) and OmniClaw operational folders (`inbox`, `outbox/pending`, `outbox/drafts`, `outbox/archive`, `outbox/dead-letter`, `notes`, `drafts`, `skills`)

### Requirement: Agent Provisioning SHALL Use Repo-Local Nanobot Agent Directories
The provisioning layer SHALL create AGENT nodes inside repo-local Nanobot agent directories under `<repo-root>/workspace/agents/<agent_name>/` by default, with a sibling `config.json` and a nested Nanobot workspace subtree.

#### Scenario: Default AGENT paths are resolved
- **WHEN** an AGENT is provisioned without explicit path overrides
- **THEN** its config path is `<repo-root>/workspace/agents/<agent_name>/config.json`
- **AND** its `workspace_root` is `<repo-root>/workspace/agents/<agent_name>/workspace`
