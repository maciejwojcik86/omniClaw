## MODIFIED Requirements

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
