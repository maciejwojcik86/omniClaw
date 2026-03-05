## MODIFIED Requirements

### Requirement: Canonical Tables SHALL Exist
The kernel data model SHALL define relational tables for `nodes`, `hierarchy`, `budgets`, `forms_ledger`, `master_skills`, `form_types`, and `form_transition_events`. The forms model SHALL persist form type/version binding, current holder snapshot, and append-only decision history needed for lifecycle auditing.

#### Scenario: Database is initialized
- **WHEN** migrations are applied to an empty database
- **THEN** all canonical tables exist with primary keys, required columns, form type registry columns, and append-only decision event schema

### Requirement: Canonical Enums SHALL Be Type-Safe
The data model SHALL define enums for node type/status, hierarchy relationship type, and skill validation state, while form type keys SHALL be snake_case and workflow statuses SHALL be validated against active form-type registry definitions.

#### Scenario: Row insertion uses enum and registry validation
- **WHEN** repository code inserts node/skill records and form instances
- **THEN** enum-constrained fields accept valid values and reject invalid values, and form type/status values are accepted only when valid for the bound form-type definition

### Requirement: Baseline Repository Operations SHALL Exist
The codebase SHALL expose repository operations to create nodes and hierarchy links, register/update form type definitions, create form instances, and append decision events.

#### Scenario: Repository creates linked nodes and form workflow records
- **WHEN** repository methods are called to register a form type, create a form instance, and append a decision event
- **THEN** canonical node links and form workflow records are persisted without manual SQL
