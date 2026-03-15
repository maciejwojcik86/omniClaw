## ADDED Requirements

### Requirement: View Node Budgets
The system SHALL provide an operational tool or API to view the current spend, daily allowance, and available virtual key metadata for any agent.

#### Scenario: Operator views budget
- **WHEN** an operator runs the cross-comparison skill/tool
- **THEN** the system returns the exact spend and limit for each agent

### Requirement: Adjust Node Allowances
The system SHALL allow operators to manually increase or decrease a node's daily allowance or per-task cap.

#### Scenario: Operator increases allowance
- **WHEN** an operator requests a budget increase for a node
- **THEN** the system updates the `current_daily_allowance` and syncs the new limit to the LiteLLM proxy
