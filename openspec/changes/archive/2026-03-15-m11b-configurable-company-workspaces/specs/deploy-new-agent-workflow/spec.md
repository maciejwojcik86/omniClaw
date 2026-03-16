## MODIFIED Requirements

### Requirement: Deployment Stage SHALL Materialize Company-Workspace Nanobot Agent Trees
The deployment stage SHALL provision agents under `<company-workspace-root>/agents/<agent_name>/` with a Nanobot `config.json`, a nested Nanobot workspace subtree, and OmniClaw operational folders required for routing.

#### Scenario: Approved deployment executes
- **WHEN** the deploy holder runs an approved deployment stage
- **THEN** the new agent directory contains `config.json` at the agent root
- **AND** the nested Nanobot workspace contains native context assets and OmniClaw routing folders
