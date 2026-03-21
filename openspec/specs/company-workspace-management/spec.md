# company-workspace-management Specification

## Purpose
Define how OmniClaw resolves one company workspace per process from the global company registry, derives company-owned runtime paths, and bootstraps or migrates those workspace assets outside the repo by default.

## Requirements
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

### Requirement: Company Workspace SHALL Own Canonical Company Runtime Assets
The selected company workspace SHALL contain the canonical company runtime assets, including active agents, active forms, active master skills, external instruction templates, Nanobot workspace templates, the per-company SQLite database, archives/logs, and retired/discontinued form and skill assets.

#### Scenario: Fresh company workspace is initialized
- **WHEN** an operator initializes a new company workspace
- **THEN** the workspace scaffold contains roots for active company assets
- **AND** contains reserved roots for archives/logs and retired/discontinued assets

#### Scenario: Retired roots are excluded from active scans
- **WHEN** the kernel scans active forms or active master skills
- **THEN** it reads only the active company roots
- **AND** it excludes retired/discontinued roots from active catalog and sync operations

### Requirement: Workspace-Local Company Config Files SHALL Not Be Canonical Runtime Inputs
The selected company workspace SHALL store editable operational assets and runtime data, but company-wide kernel settings SHALL come from the global OmniClaw config rather than from a workspace-local company config file.

#### Scenario: Kernel loads company settings
- **WHEN** the kernel needs budgeting, instructions, skill-default, hierarchy-anchor, model, or runtime settings for a selected company
- **THEN** it reads those settings from the selected company entry in the global OmniClaw config
- **AND** it does not require `<company-workspace-root>/config.json` or `<company-workspace-root>/company_config.json`

#### Scenario: Default database remains under selected company workspace
- **WHEN** the operator does not provide an explicit database URL
- **THEN** the kernel resolves SQLite to `<company-workspace-root>/omniclaw.db`

### Requirement: OmniClaw SHALL Support Multiple Isolated Company Environments Through Global Registry Selection
OmniClaw SHALL support multiple isolated company environments by allowing separate launches to select different company entries from the global registry.

#### Scenario: Two companies are launched separately
- **WHEN** two OmniClaw processes start with different `--company` values
- **THEN** each process reads its own forms, skills, templates, settings, and database from its selected workspace
- **AND** no company-owned runtime state is shared implicitly between those roots

### Requirement: Company Workspace Setup SHALL Use Direct Registry-Backed Initialization
The system SHALL treat the selected external company workspace as the only source of truth and SHALL rely on direct workspace creation plus global-registry registration rather than on repo-local bootstrap or migration flows.

#### Scenario: Operator prepares a fresh company workspace
- **WHEN** an operator creates a company workspace following the documented requirements
- **THEN** the required directory layout exists under the selected workspace root
- **AND** the selected company entry is created or updated in the global OmniClaw config

#### Scenario: Retired repo-local bootstrap entrypoints are used
- **WHEN** an operator invokes a retired repo-local bootstrap or migration entrypoint
- **THEN** the command fails fast
- **AND** points the operator at the direct company-workspace setup documentation
