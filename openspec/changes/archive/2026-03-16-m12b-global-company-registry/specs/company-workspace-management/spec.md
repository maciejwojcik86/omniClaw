## MODIFIED Requirements

### Requirement: Kernel Process SHALL Resolve Company Context From Global OmniClaw Config
The kernel SHALL resolve exactly one active company context per process start from the global OmniClaw config file, and the default global config path SHALL be `<user-home>/.omniClaw/config.json`.

#### Scenario: Company slug is supplied at startup
- **WHEN** an operator starts the kernel with `--company <slug-or-display-name>`
- **THEN** the kernel loads the global OmniClaw config file
- **AND** resolves the matching company entry from `companies`
- **AND** derives the company workspace root from that entry

#### Scenario: One company exists and no company is supplied
- **WHEN** the global config contains exactly one registered company and the operator omits `--company`
- **THEN** the kernel auto-selects that sole company entry

#### Scenario: Multiple companies exist and no company is supplied
- **WHEN** the global config contains more than one registered company and the operator omits `--company`
- **THEN** startup fails with a clear configuration error

### Requirement: Workspace Roots Referenced By Global Config SHALL Exist
The kernel SHALL fail fast when the selected company entry references a workspace root that does not exist.

#### Scenario: Missing workspace root is configured
- **WHEN** the selected company entry points at a missing workspace directory
- **THEN** the kernel refuses to start
- **AND** reports which company entry and workspace path are invalid

### Requirement: Workspace-Local Company Config Files SHALL Not Be Canonical Runtime Inputs
The selected company workspace SHALL store editable operational assets and runtime data, but company-wide kernel settings SHALL come from the global OmniClaw config rather than from a workspace-local company config file.

#### Scenario: Kernel loads company settings
- **WHEN** the kernel needs budgeting, instructions, skill-default, hierarchy-anchor, model, or runtime settings for a selected company
- **THEN** it reads those settings from the selected company entry in the global OmniClaw config
- **AND** it does not require `<company-workspace-root>/config.json` or `<company-workspace-root>/company_config.json`
