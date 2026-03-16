## ADDED Requirements

### Requirement: Kernel SHALL Resolve One Active Company Workspace Per Process
The kernel SHALL resolve exactly one active company workspace root for each process start, and the default root SHALL be `<user-home>/.omniClaw/workspace` when no explicit override is provided.

#### Scenario: Explicit company workspace root is provided
- **WHEN** an operator starts the kernel with an explicit company workspace root override
- **THEN** the kernel derives company-owned runtime paths from that root
- **AND** it MUST NOT implicitly fall back to `<repo-root>/workspace`

#### Scenario: No explicit workspace root is provided
- **WHEN** the kernel starts without a company workspace override
- **THEN** it defaults the company workspace root to `<user-home>/.omniClaw/workspace`
- **AND** derives the default company config and SQLite database paths from that root

### Requirement: Company Workspace SHALL Own Canonical Company Runtime Assets
The selected company workspace SHALL contain the canonical company runtime assets, including active agents, active forms, active master skills, external instruction templates, Nanobot workspace templates, company settings, SQLite database, archives/logs, and retired/discontinued form and skill assets.

#### Scenario: Fresh company workspace is initialized
- **WHEN** an operator initializes a new company workspace
- **THEN** the workspace scaffold contains roots for active company assets
- **AND** contains reserved roots for archives/logs and retired/discontinued assets

#### Scenario: Retired roots are excluded from active scans
- **WHEN** the kernel scans active forms or active master skills
- **THEN** it reads only the active company roots
- **AND** it excludes retired/discontinued roots from active catalog and sync operations

### Requirement: Company Workspace Configuration SHALL Default To Workspace-Local Config And Database Files
The kernel SHALL default the company settings file to `<company-workspace-root>/config.json` and SHALL default the SQLite database location to `<company-workspace-root>/omniclaw.db` unless explicit overrides are provided.

#### Scenario: Defaults are derived from selected company workspace
- **WHEN** the operator provides only a company workspace root
- **THEN** the kernel resolves company settings from `<company-workspace-root>/config.json`
- **AND** resolves the default SQLite database from `<company-workspace-root>/omniclaw.db`

#### Scenario: Explicit overrides are honored
- **WHEN** the operator provides an explicit company config path or database URL
- **THEN** the kernel uses those explicit values
- **AND** continues to derive the remaining company-owned asset roots from the selected company workspace root

### Requirement: OmniClaw SHALL Support Multiple Isolated Company Environments Through Workspace Selection
OmniClaw SHALL support multiple isolated company environments by allowing separate launches to select different company workspace roots and config/database inputs.

#### Scenario: Two company workspaces are launched separately
- **WHEN** two OmniClaw processes start with different company workspace roots
- **THEN** each process reads its own forms, skills, templates, config, and database
- **AND** no company-owned runtime state is shared implicitly between those roots

### Requirement: Kernel SHALL Provide Company Workspace Bootstrap And Migration Tooling
The system SHALL provide tooling to scaffold a fresh company workspace and to migrate an existing repo-local company workspace into a selected external company workspace.

#### Scenario: Operator bootstraps a fresh company workspace
- **WHEN** an operator runs the company-workspace init flow
- **THEN** the required directory layout and baseline config artifacts are created under the selected workspace root

#### Scenario: Operator migrates repo-local workspace content
- **WHEN** an operator runs the migration flow against an existing repo-local OmniClaw workspace
- **THEN** company-owned runtime assets are copied or moved into the selected company workspace
- **AND** the tooling reports any missing or skipped assets before the operator switches the kernel to the new root
