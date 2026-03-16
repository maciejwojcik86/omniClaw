# canonical-state-schema Specification

## Purpose
Define the canonical relational state model, enum-constrained entities, and baseline repository behavior for nodes, hierarchy, budgets, forms, and master skills.
## Requirements
### Requirement: Canonical Tables SHALL Exist
The kernel data model SHALL define relational tables for `nodes`, `hierarchy`, `budgets`, `forms_ledger`, `master_skills`, and `node_skill_assignments`, and the forms ledger SHALL persist sender/target and routing metadata needed for message lifecycle auditing.

#### Scenario: Database is initialized
- **WHEN** migrations are applied to an empty database
- **THEN** all canonical tables exist with primary keys, required columns, and message-routing metadata fields in `forms_ledger`
- **AND** `node_skill_assignments` exists to track effective skill delivery state per agent

### Requirement: Canonical Enums SHALL Be Type-Safe
The data model SHALL define enums for node type/status, form type/status, skill validation state, master-skill lifecycle state, and node skill assignment source, and persist them in table fields, including message-routing values required for IPC lifecycle tracking.

#### Scenario: Row insertion uses enums
- **WHEN** repository code inserts node, form, master-skill, and node-skill-assignment records
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

### Requirement: Canonical Node Metadata SHALL Track Instruction Template Inputs
The canonical node model SHALL persist the role label and external instruction template root needed to render managed AGENT instructions.

#### Scenario: Node metadata migration completes
- **WHEN** the database is migrated for the context injector change
- **THEN** canonical node records include `role_name` and `instruction_template_root` columns without losing existing node data

#### Scenario: Repository persists instruction metadata
- **WHEN** higher-level services create or update a node with instruction metadata
- **THEN** repository operations persist and return the node role label and template-root path alongside existing runtime metadata

