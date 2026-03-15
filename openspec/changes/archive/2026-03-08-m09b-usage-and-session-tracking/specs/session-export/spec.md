## ADDED Requirements

### Requirement: Export Native App Sessions
The system SHALL provide an automated or API-driven capability to export native Nanobot conversation sessions.

#### Scenario: Operator wants backup of session history
- **WHEN** an operator invokes the session export endpoint targeting a specific agent node
- **THEN** the system reads the agent's JSONL session representations from their local workspace
- **THEN** the system copies or persists the structured log sequence into centralized observability tables/files

### Requirement: Include Metadata in Export
The system SHALL attach node identity and usage tracking metrics natively when exporting a serialized session copy.

#### Scenario: Validating exported metadata
- **WHEN** the session is exported
- **THEN** identifying agent metadata (e.g. `node_id`, `role_name`) is tied to the exported record
