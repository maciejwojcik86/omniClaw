# global-company-registry Specification

## Purpose
Define the host-level OmniClaw config that registers companies and serves as the canonical source of company-wide settings for the kernel.

## Requirements
### Requirement: OmniClaw SHALL Maintain A Global Company Registry Config
The app SHALL maintain one global config file containing registered companies and their canonical settings.

#### Scenario: Global config stores company entries
- **WHEN** OmniClaw reads its global config
- **THEN** it finds a `companies` object keyed by stable company slug
- **AND** each company entry contains display name, workspace root, and company-level settings

### Requirement: Company Registry SHALL Be The Source Of Truth For Company Settings
The company registry SHALL be the canonical source for company-wide settings used by the kernel.

#### Scenario: Budget settings are needed
- **WHEN** the budget engine loads company configuration
- **THEN** it resolves `daily_company_budget_usd`, `root_allocator_node`, and `reset_time_utc` from the selected company entry

#### Scenario: Instruction access settings are needed
- **WHEN** the instructions service needs company access-scope policy
- **THEN** it resolves that policy from the selected company entry

#### Scenario: Default skill assignment settings are needed
- **WHEN** provisioning or skill-sync logic needs default company loose skills
- **THEN** it resolves those defaults from the selected company entry

#### Scenario: Model settings are needed
- **WHEN** the kernel or helpers need the company model catalog
- **THEN** they resolve that catalog from the selected company entry

### Requirement: Company Registry Resolution SHALL Support Display Names
The CLI SHALL allow a company to be addressed by its stable slug or by its display name.

#### Scenario: Display name uniquely identifies company
- **WHEN** the operator passes a unique display name instead of a slug
- **THEN** OmniClaw resolves the matching company entry and starts successfully

#### Scenario: Duplicate display names would be ambiguous
- **WHEN** more than one company entry shares the same display name
- **THEN** OmniClaw refuses display-name resolution and requires the stable slug
