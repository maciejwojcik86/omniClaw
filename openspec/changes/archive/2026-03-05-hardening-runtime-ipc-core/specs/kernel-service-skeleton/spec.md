## ADDED Requirements

### Requirement: Kernel Startup SHALL Enforce Migration-First Schema Contract
Kernel startup MUST verify database revision is aligned with Alembic head and MUST NOT implicitly create schema tables.

#### Scenario: Migrated database starts successfully
- **WHEN** database revision is at Alembic head
- **THEN** app startup succeeds

#### Scenario: Unmigrated database fails startup
- **WHEN** database revision is missing or behind head
- **THEN** app startup fails with migration guidance instead of creating tables implicitly
