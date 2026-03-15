## MODIFIED Requirements

### Requirement: View Node Budgets
The system SHALL provide an operational tool or API for managers to view the budget state of themselves and their direct reports, including budget mode, fresh daily inflow, rollover reserve, effective enforced cap, current spend, remaining budget, and review-required status.

#### Scenario: Manager views team budget
- **WHEN** a manager requests a team budget view for their own node
- **THEN** the system returns the manager row plus each direct report row with the exact live budget state for that management layer

### Requirement: Adjust Node Allowances
The system SHALL allow managers to update direct-report percentage allocations for their own team. The system SHALL reject direct allowance edits as authoritative updates for hierarchy-managed nodes unless the action is explicitly invoked as break-glass behavior.

#### Scenario: Manager updates team allocations
- **WHEN** a manager submits a direct-report allocation update whose child percentages total less than or equal to one hundred percent
- **THEN** the system persists the new percentages, recomputes affected subtree budgets immediately, and returns the updated team view

#### Scenario: Direct allowance edit is rejected for managed node
- **WHEN** an operator requests a flat allowance update for a node that belongs to a hierarchical team budget
- **THEN** the system rejects the update unless the request explicitly uses the break-glass path
