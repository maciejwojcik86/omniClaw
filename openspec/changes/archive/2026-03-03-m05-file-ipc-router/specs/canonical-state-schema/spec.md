## MODIFIED Requirements

### Requirement: Canonical Enums SHALL Be Type-Safe
The data model SHALL define enums for node type/status, form type/status, and skill validation state, and persist them in table fields, including message-routing values required for IPC lifecycle tracking.

#### Scenario: Row insertion uses enums
- **WHEN** repository code inserts node/form/skill records including `MESSAGE` form entries and routing lifecycle statuses
- **THEN** enum-constrained fields accept valid values and reject invalid values

### Requirement: Canonical Tables SHALL Exist
The kernel data model SHALL define relational tables for `nodes`, `hierarchy`, `budgets`, `forms_ledger`, and `master_skills`, and the forms ledger SHALL persist sender/target and routing metadata needed for message lifecycle auditing.

#### Scenario: Database is initialized
- **WHEN** migrations are applied to an empty database
- **THEN** all canonical tables exist with primary keys, required columns, and message-routing metadata fields in `forms_ledger`
