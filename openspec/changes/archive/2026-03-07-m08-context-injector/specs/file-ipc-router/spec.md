## ADDED Requirements

### Requirement: IPC Scan SHALL Refresh Active Agent Instructions Before Routing
Each IPC scan cycle SHALL refresh rendered `AGENTS.md` files for active AGENT nodes before processing queued outbound forms.

#### Scenario: Manual scan refreshes AGENT instructions
- **WHEN** an operator triggers an IPC scan action
- **THEN** the kernel performs the AGENT instruction render sweep before processing queued form files

#### Scenario: Background auto-scan refreshes AGENT instructions
- **WHEN** the background IPC scan loop executes
- **THEN** the same render sweep runs before queued form processing without requiring a separate scheduler

### Requirement: Instruction Render Failures SHALL Not Block Form Routing
Instruction render failures during an IPC scan MUST be reported separately and MUST NOT prevent queued-form routing for other nodes in the same scan cycle.

#### Scenario: One AGENT render fails during scan
- **WHEN** the scan encounters a render error for one AGENT template
- **THEN** the kernel keeps the last good `AGENTS.md` for that node
- **AND** continues processing queued form files for the rest of the scan cycle
