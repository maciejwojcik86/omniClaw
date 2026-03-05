# kernel-service-skeleton Specification

## Purpose
Provide the baseline kernel runtime shell: FastAPI app factory, structured startup behavior, and health check endpoint required by subsequent milestones.
## Requirements
### Requirement: Kernel Service SHALL Expose a Health Endpoint
The kernel service SHALL expose `GET /healthz` that returns success status without requiring authentication.

#### Scenario: Health endpoint check succeeds
- **WHEN** a client calls `GET /healthz`
- **THEN** the service returns HTTP 200 with a JSON body indicating status `ok`

### Requirement: Kernel Service SHALL Use an App Factory
The kernel runtime SHALL provide an application factory function that builds and returns a configured FastAPI app instance.

#### Scenario: App factory is used by entrypoint
- **WHEN** the process starts
- **THEN** the entrypoint loads configuration and instantiates the app through the factory

### Requirement: Kernel Service SHALL Initialize Structured Logging
The service SHALL initialize logging in a structured format suitable for daemon and API debugging.

#### Scenario: Service initializes
- **WHEN** the app starts
- **THEN** logs are emitted using the configured structured formatter

### Requirement: Kernel Startup SHALL Enforce Migration-First Schema Contract
Kernel startup MUST verify database revision is aligned with Alembic head and MUST NOT implicitly create schema tables.

#### Scenario: Migrated database starts successfully
- **WHEN** database revision is at Alembic head
- **THEN** app startup succeeds

#### Scenario: Unmigrated database fails startup
- **WHEN** database revision is missing or behind head
- **THEN** app startup fails with migration guidance instead of creating tables implicitly

