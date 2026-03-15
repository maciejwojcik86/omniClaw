## MODIFIED Requirements

### Requirement: AGENTS Template Rendering SHALL Use Allowlisted Placeholders
The context injector SHALL resolve the existing instruction placeholders plus budget-awareness placeholders for each AGENT node, and SHALL reject unknown placeholders during preview or template update actions.

#### Scenario: Budget placeholders render successfully
- **WHEN** a template uses supported variables such as `{{budget.mode}}`, `{{budget.daily_inflow_usd}}`, `{{budget.rollover_reserve_usd}}`, `{{budget.remaining_usd}}`, `{{budget.review_required_notice}}`, and `{{budget.direct_team_summary}}`
- **THEN** the kernel returns rendered AGENTS content with live budget values resolved from canonical state

#### Scenario: Unknown placeholder is rejected
- **WHEN** a template includes an unsupported placeholder
- **THEN** preview and template update actions fail with validation details and do not replace the stored template

### Requirement: Instructions Access SHALL Follow Company-Configured Hierarchy Rules
The kernel SHALL continue to authorize instruction-management actions using the management hierarchy and SHALL distribute all manager-only master skills to nodes with subordinates.

#### Scenario: Manager skill distribution installs organization manager skills
- **WHEN** the kernel syncs manager skill distribution
- **THEN** any node with subordinates receives the manager instruction skill and the manager team-budget skill in its workspace skill directory
