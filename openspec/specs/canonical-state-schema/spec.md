# canonical-state-schema Specification

## Purpose
Define the canonical relational state model, enum-constrained entities, and baseline repository behavior for nodes, hierarchy, budgets, forms, and master skills.
## Requirements
### Requirement: Canonical Tables SHALL Exist
The kernel data model SHALL define relational tables for `nodes`, `hierarchy`, `budgets`, `forms_ledger`, and `master_skills`, and the forms ledger SHALL persist sender/target and routing metadata needed for message lifecycle auditing.

#### Scenario: Database is initialized
- **WHEN** migrations are applied to an empty database
- **THEN** all canonical tables exist with primary keys, required columns, and message-routing metadata fields in `forms_ledger`

### Requirement: Canonical Enums SHALL Be Type-Safe
The data model SHALL define enums for node type/status, form type/status, and skill validation state, and persist them in table fields, including message-routing values required for IPC lifecycle tracking.

#### Scenario: Row insertion uses enums
- **WHEN** repository code inserts node/form/skill records including `MESSAGE` form entries and routing lifecycle statuses
- **THEN** enum-constrained fields accept valid values and reject invalid values

### Requirement: Hierarchy Linkage SHALL Be Representable
The schema SHALL support parent-child relationships between nodes through the hierarchy table.

#### Scenario: Human manages agent
- **WHEN** a HUMAN node and AGENT node are inserted with a hierarchy row
- **THEN** the relationship is persisted and queryable by repository methods

### Requirement: Baseline Repository Operations SHALL Exist
The codebase SHALL expose repository operations to create nodes and hierarchy links for use by higher-level services.

#### Scenario: Repository creates linked nodes
- **WHEN** repository methods are called in sequence
- **THEN** a HUMAN parent and AGENT child are created and linked without manual SQL

### Requirement: Form Snapshot Writes SHALL Use Optimistic Concurrency Control
Canonical `forms_ledger` snapshots MUST include versioned concurrency metadata used to detect stale writes.

#### Scenario: Snapshot transition updates version
- **WHEN** a valid form transition commits
- **THEN** form snapshot version increments and event sequence remains unique

#### Scenario: Stale snapshot write is rejected
- **WHEN** transition request is applied against stale form version
- **THEN** write is rejected with deterministic conflict outcome and no partial state change

### Requirement: Canonical Form Metadata SHALL Track Dead-Letter Context Fields
Canonical form metadata model MUST preserve dead-letter and failure-reason fields for failed IPC lifecycle outcomes.

#### Scenario: Failed IPC handling records dead-letter context
- **WHEN** IPC processing marks queued file as undelivered and dead-letters source artifact
- **THEN** dead-letter/failure context fields remain available for deterministic response/reporting and follow-up workflows

