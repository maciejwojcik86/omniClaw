## ADDED Requirements

### Requirement: Deploy Workflow Guidance SHALL Expose Default And Post-Deploy Skill Operations
The canonical `deploy-new-nanobot` stage skill SHALL document the company default loose skills applied at provisioning time and SHALL provide deployers with endpoint-backed tools for listing active loose skills and applying batch post-deploy assignments.

#### Scenario: Deployment skill package is published
- **WHEN** the canonical `deploy_new_agent` workflow assets are synced from workspace packages
- **THEN** the `deploy-new-nanobot` stage skill documents the default loose-skill set
- **AND** references packaged tools for listing active loose skills and assigning multiple loose skills after deployment
