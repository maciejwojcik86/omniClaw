## ADDED Requirements

### Requirement: Generate LiteLLM Virtual Keys
The system SHALL generate a unique LiteLLM virtual key for a node upon deployment or manual request, storing it in the canonical database.

#### Scenario: Key Generation on Deployment
- **WHEN** a new agent node is provisioned
- **THEN** a virtual key is generated via the LiteLLM proxy and assigned to the node's budget record

### Requirement: Ingest Cost Data
The system SHALL ingest spend and usage data from the LiteLLM proxy and update the node's budget spend record.

#### Scenario: Cost Sync
- **WHEN** the ingestion daemon runs
- **THEN** it pulls current spend from the proxy and updates `current_spend` for the node in the `budgets` table
