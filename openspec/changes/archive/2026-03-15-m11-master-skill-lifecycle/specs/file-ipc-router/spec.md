## MODIFIED Requirements

### Requirement: IPC Scan SHALL Refresh Active Agent Instructions Before Routing
Each IPC scan cycle SHALL refresh rendered `AGENTS.md` files and approved workspace `skills/` contents for active AGENT nodes before processing queued outbound forms.

#### Scenario: Manual scan refreshes instructions and approved skills
- **WHEN** an operator triggers an IPC scan action
- **THEN** the kernel performs the AGENT instruction render sweep before processing queued form files
- **AND** reconciles each active AGENT workspace `skills/` directory from approved skill assignments in the same pre-pass

#### Scenario: Background auto-scan refreshes instructions and approved skills
- **WHEN** the background IPC scan loop executes
- **THEN** the same render-and-skill reconciliation sweep runs before queued form processing without requiring a separate scheduler
