## ADDED Requirements

### Requirement: Instruction Template Defaults SHALL Resolve From The Selected Company Workspace
The kernel SHALL derive default external instruction-template roots and default AGENTS template sources from the selected company workspace rather than from repo-local runtime assets.

#### Scenario: Provisioned agent receives default external template root
- **WHEN** the kernel needs to derive an instruction-template root for an AGENT without an explicit override
- **THEN** it resolves that root under `<company-workspace-root>/nanobots_instructions/<agent_name>/`

#### Scenario: Default AGENTS template source is resolved
- **WHEN** the kernel seeds or repairs a missing default AGENTS template
- **THEN** it loads the baseline template from `<company-workspace-root>/nanobot_workspace_templates/AGENTS.md`
- **AND** it does not depend on a repo-local `workspace/nanobot_workspace_templates/AGENTS.md` default
