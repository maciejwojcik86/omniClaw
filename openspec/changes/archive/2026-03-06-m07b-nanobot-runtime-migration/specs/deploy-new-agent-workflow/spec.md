## ADDED Requirements

### Requirement: Canonical Deploy Workflow SHALL Target Nanobot Deployment Skill
The canonical `deploy_new_agent` workflow SHALL route its deployment stage to the `deploy-new-nanobot` skill package.

#### Scenario: Workspace workflow is synced
- **WHEN** the active `deploy_new_agent` workflow is loaded from workspace assets
- **THEN** the `AGENT_DEPLOYMENT` stage requires `deploy-new-nanobot`

### Requirement: Deployment Stage SHALL Materialize Repo-Local Nanobot Agent Trees
The deployment stage SHALL provision agents under `<repo-root>/workspace/agents/<agent_name>/` with a Nanobot `config.json`, a nested Nanobot workspace subtree, and OmniClaw operational folders required for routing.

#### Scenario: Approved deployment executes
- **WHEN** the deploy holder runs an approved deployment stage
- **THEN** the new agent directory contains `config.json` at the agent root
- **AND** the nested Nanobot workspace contains native context assets and OmniClaw routing folders

### Requirement: Legacy Nullclaw Deployment Assets SHALL Remain Optional
The migration SHALL keep the legacy `deploy-new-claw-agent` skill package available for manual or backward-compatibility use, but it SHALL NOT remain the default stage skill in the canonical deploy workflow.

#### Scenario: Migration completes
- **WHEN** deployment assets are published after the Nanobot migration
- **THEN** `deploy-new-claw-agent` remains available in the repo
- **AND** the canonical `deploy_new_agent` workflow references `deploy-new-nanobot` instead
