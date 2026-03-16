## ADDED Requirements

### Requirement: Discover Active Agents Canonically
The system SHALL provide a canonical agent discovery response that lists active agents with enough metadata for autonomous workflow planning and validation.

#### Scenario: Operator lists active agents
- **WHEN** an operator or supervising agent requests the active agent catalog
- **THEN** the system returns active nodes with identity, role/description, runtime availability, provider/model summary, key presence, and budget summary metadata

#### Scenario: Caller avoids repo discovery
- **WHEN** the caller needs to determine what agents are available
- **THEN** the workflow does not require scanning `workspace/agents/` or reading repo-local config files directly

### Requirement: Report Budget State Canonically
The system SHALL provide a canonical budget report response suitable for before/after comparison of spend and remaining budget.

#### Scenario: Caller captures budget baseline
- **WHEN** a caller requests the budget report before invoking agents
- **THEN** the system returns organization-wide and per-node budget state in a stable machine-readable structure

#### Scenario: Caller captures budget after usage
- **WHEN** a caller requests the budget report after invoking agents and reconciling costs as required
- **THEN** the system returns updated spend and remaining-budget values suitable for delta comparison

### Requirement: Invoke Agent Prompts Through The Kernel
The system SHALL provide a canonical kernel-mediated surface for triggering a low-cost prompt run against a target agent.

#### Scenario: Supervising caller runs cheap verification prompt
- **WHEN** a caller submits a target agent and a message with a session key
- **THEN** the system executes the run through the supported runtime path and returns structured run metadata including the session key and response status

#### Scenario: Invalid target agent is rejected
- **WHEN** the caller specifies an unknown or ineligible target agent
- **THEN** the system rejects the request with a clear error response

### Requirement: Query Usage And Session Summaries Canonically
The system SHALL expose read/report responses for usage and session summaries without requiring direct DB access by the caller.

#### Scenario: Caller retrieves session usage summary
- **WHEN** a caller requests a usage summary for a known session key
- **THEN** the system returns llm-call counts, token totals, cost totals, timestamps, and correlation metadata for that session

#### Scenario: Caller retrieves node recent sessions
- **WHEN** a caller requests recent sessions for a node
- **THEN** the system returns a stable list of recent sessions with summary telemetry for each

### Requirement: Verification Workflow Uses Supported Scripts And Endpoints
The system SHALL provide or document packaged helper scripts for the final workflow, and those scripts SHALL use only supported kernel endpoints or explicit runtime contracts intended for future agents.

#### Scenario: Operator runs canonical verification workflow
- **WHEN** the operator performs the budget verification workflow
- **THEN** each step is executed using approved scripts/endpoints rather than repo discovery or direct SQLite inspection

#### Scenario: Diagnostic tools remain non-canonical
- **WHEN** a developer uses a direct DB reader or repo-local diagnostic script
- **THEN** that tool is not treated as the canonical proof-path for autonomous workflow completion
