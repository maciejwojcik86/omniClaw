## ADDED Requirements

### Requirement: Agent Provisioning SHALL Seed Default Loose Skills
Agent provisioning SHALL assign company-configured default loose skills to new AGENT nodes using the canonical master-skill assignment ledger.

#### Scenario: New agent receives default company skills
- **WHEN** an AGENT is provisioned and `workspace/company_config.json` declares default loose skills
- **THEN** the kernel records `DEFAULT` node-skill-assignment rows for each configured active loose skill
- **AND** excludes form-linked skills from that default list

### Requirement: Agent Provisioning SHALL Reconcile Initial Approved Skills
The provisioning flow SHALL reconcile the new AGENT workspace `skills/` directory after default and form-stage assignments are determined.

#### Scenario: Provisioned agent starts with approved skills only
- **WHEN** agent provisioning completes successfully
- **THEN** the kernel rebuilds the new agent workspace `skills/` directory from approved assignments
- **AND** the response includes the resulting skill-sync summary alongside the rendered instructions summary
