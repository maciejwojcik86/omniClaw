## MODIFIED Requirements

### Requirement: Runtime Bootstrap SHALL Capture Run Metadata
The runtime bootstrap workflow SHALL capture run metadata for every execution attempt, including retry classification and deferred retry scheduling outcomes when a run fails with a retryable LLM/API condition.

#### Scenario: Runtime launch completes
- **WHEN** the runtime command exits (success or failure)
- **THEN** run metadata includes start/end timestamps, effective command, exit status, and output artifact paths

#### Scenario: Retryable failure schedules deferred work
- **WHEN** runtime execution fails with a retryable LLM/API condition
- **THEN** run metadata records the normalized failure classification
- **AND** includes whether a deferred retry was scheduled and when the next attempt is due
