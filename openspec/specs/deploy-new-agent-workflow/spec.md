# deploy-new-agent-workflow Specification

## Purpose
Define the canonical `deploy_new_agent` workflow requirements, including deployment-stage skill routing and runtime-specific provisioning expectations for Nanobot-backed agents.
## Requirements
### Requirement: Canonical Deploy Workflow SHALL Target Nanobot Deployment Skill
The canonical `deploy_new_agent` workflow SHALL route its deployment stage to the `deploy-new-nanobot` skill package.

#### Scenario: Workspace workflow is synced
- **WHEN** the active `deploy_new_agent` workflow is loaded from workspace assets
- **THEN** the `AGENT_DEPLOYMENT` stage requires `deploy-new-nanobot`

### Requirement: Deployment Stage SHALL Materialize Company-Workspace Nanobot Agent Trees
The deployment stage SHALL provision agents under `<company-workspace-root>/agents/<agent_name>/` with a Nanobot `config.json`, a nested Nanobot workspace subtree, and OmniClaw operational folders required for routing.

#### Scenario: Approved deployment executes
- **WHEN** the deploy holder runs an approved deployment stage
- **THEN** the new agent directory contains `config.json` at the agent root
- **AND** the nested Nanobot workspace contains native context assets and OmniClaw routing folders

### Requirement: Deploy Workflow SHALL Use Nanobot-Native Deployment Assets
The canonical deploy workflow SHALL use Nanobot-native skill and CLI naming, and SHALL NOT depend on legacy deployment skill packages or flag aliases.

#### Scenario: Migration completes
- **WHEN** deployment assets are published after the Nanobot migration
- **THEN** the canonical `deploy_new_agent` workflow references `deploy-new-nanobot`
- **AND** operator guidance references Nanobot runtime commands and config/workspace paths

### Requirement: Deploy Workflow Guidance SHALL Expose Default And Post-Deploy Skill Operations
The canonical `deploy-new-nanobot` stage skill SHALL document the company default loose skills applied at provisioning time and SHALL provide deployers with endpoint-backed tools for listing active loose skills and applying batch post-deploy assignments.

#### Scenario: Deployment skill package is published
- **WHEN** the canonical `deploy_new_agent` workflow assets are synced from workspace packages
- **THEN** the `deploy-new-nanobot` stage skill documents the default loose-skill set
- **AND** references packaged tools for listing active loose skills and assigning multiple loose skills after deployment
