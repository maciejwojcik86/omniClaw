# canonical-state-schema Specification

## Purpose
Define the canonical relational state model, enum-constrained entities, and baseline repository behavior for nodes, hierarchy, budgets, forms, and master skills.
## Requirements
### Requirement: Canonical Tables SHALL Exist
The kernel data model SHALL define relational tables for `nodes`, `hierarchy`, `budgets`, `forms_ledger`, and `master_skills`.

#### Scenario: Database is initialized
- **WHEN** migrations are applied to an empty database
- **THEN** all canonical tables exist with primary keys and required columns

### Requirement: Canonical Enums SHALL Be Type-Safe
The data model SHALL define enums for node type/status, form type/status, and skill validation state, and persist them in table fields.

#### Scenario: Row insertion uses enums
- **WHEN** repository code inserts node/form/skill records
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
