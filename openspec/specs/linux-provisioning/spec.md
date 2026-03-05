# linux-provisioning Specification

## Purpose
Define safe, testable Linux user/workspace provisioning primitives for OmniClaw agent onboarding, including mock/system adapters, deterministic workspace scaffolding, and manager-aware permission policy.
## Requirements
### Requirement: Provisioning Interface SHALL Support Mock and System Modes
The kernel provisioning layer SHALL provide interchangeable adapters for `mock` and `system` execution to support safe development and production rollout.

#### Scenario: Test environment uses mock adapter
- **WHEN** provisioning is executed in tests
- **THEN** no real Linux users are created and all operations are captured deterministically

### Requirement: Workspace Scaffold SHALL Match OmniClaw Contract
Provisioning SHALL create the required workspace tree for a new agent.

#### Scenario: New agent is provisioned
- **WHEN** the provisioning workflow completes
- **THEN** required folders/files exist under the agent workspace (`inbox`, `outbox/pending`, `outbox/drafts`, `outbox/archive`, `outbox/dead-letter`, `notes`, `drafts`, `skills`, templates)

### Requirement: Ownership and Group Rules SHALL Be Applied
Provisioning SHALL apply ownership and group permissions to support manager oversight of subordinate workspaces.

#### Scenario: Manager-subordinate relationship exists
- **WHEN** a subordinate workspace is provisioned
- **THEN** owner and manager group permissions are applied according to policy
