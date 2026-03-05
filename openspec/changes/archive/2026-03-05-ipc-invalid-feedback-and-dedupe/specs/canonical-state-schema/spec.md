## ADDED Requirements

### Requirement: Canonical Form Metadata SHALL Track Dead-Letter Context Fields
Canonical form metadata model MUST preserve dead-letter and failure-reason fields for failed IPC lifecycle outcomes.

#### Scenario: Failed IPC handling records dead-letter context
- **WHEN** IPC processing marks queued file as undelivered and dead-letters source artifact
- **THEN** dead-letter/failure context fields remain available for deterministic response/reporting and follow-up workflows
