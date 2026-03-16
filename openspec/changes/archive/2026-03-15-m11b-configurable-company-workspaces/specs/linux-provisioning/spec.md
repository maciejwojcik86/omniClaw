## MODIFIED Requirements

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

### Requirement: Agent Provisioning SHALL Seed Default Loose Skills From The Selected Company Configuration
Agent provisioning SHALL resolve company-configured default loose skills from the selected company settings file and assign them to new AGENT nodes using the canonical master-skill assignment ledger.

#### Scenario: New agent receives default company skills
- **WHEN** an AGENT is provisioned and the selected company `config.json` declares default loose skills
- **THEN** the kernel records `DEFAULT` node-skill-assignment rows for each configured active loose skill
- **AND** excludes form-linked skills from that default list
