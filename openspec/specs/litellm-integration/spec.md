# litellm-integration Specification

## Purpose
TBD - created by archiving change m09-litellm-key-management. Update Purpose after archive.
## Requirements
### Requirement: Generate LiteLLM Virtual Keys
The system SHALL generate a unique LiteLLM virtual key for a node upon deployment or manual request, storing it in the canonical database.

#### Scenario: Key Generation on Deployment
- **WHEN** a new agent node is provisioned
- **THEN** a virtual key is generated via the LiteLLM proxy and assigned to the node's budget record

### Requirement: Ingest Cost Data
The system SHALL ingest spend and usage data from the LiteLLM proxy for metered nodes and update the node's budget spend record without overwriting waterfall-managed reserve or review state.

#### Scenario: Cost sync preserves waterfall state
- **WHEN** the ingestion daemon or API syncs spend for a metered node
- **THEN** it updates that node's `current_spend` and provider-reported cap fields without clearing reserve, review-required, or saved allocation data

#### Scenario: Free node is skipped during cap reconciliation
- **WHEN** the system encounters a node in `free` mode during cap reconciliation
- **THEN** it omits provider cap updates for that node while leaving its waterfall reporting state intact

