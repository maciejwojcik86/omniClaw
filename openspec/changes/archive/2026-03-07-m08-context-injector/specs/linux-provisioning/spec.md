## ADDED Requirements

### Requirement: Agent Provisioning SHALL Create External Instruction Template Roots
Agent provisioning SHALL create and persist an external instruction template root for each provisioned AGENT under `workspace/nanobots_instructions/<agent_name>/`.

#### Scenario: Provisioned agent receives template root
- **WHEN** an AGENT is provisioned successfully
- **THEN** the kernel creates `workspace/nanobots_instructions/<agent_name>/`
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
