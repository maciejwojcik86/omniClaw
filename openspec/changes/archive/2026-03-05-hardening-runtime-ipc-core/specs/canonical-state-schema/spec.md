## ADDED Requirements

### Requirement: Form Snapshot Writes SHALL Use Optimistic Concurrency Control
Canonical `forms_ledger` snapshots MUST include versioned concurrency metadata used to detect stale writes.

#### Scenario: Snapshot transition updates version
- **WHEN** a valid form transition commits
- **THEN** form snapshot version increments and event sequence remains unique

#### Scenario: Stale snapshot write is rejected
- **WHEN** transition request is applied against stale form version
- **THEN** write is rejected with deterministic conflict outcome and no partial state change
