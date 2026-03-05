# runtime-ipc-hardening Specification

## Purpose
TBD - created by archiving change hardening-runtime-ipc-core. Update Purpose after archive.
## Requirements
### Requirement: Runtime Gateway Start SHALL Reject Invalid Host Inputs
The kernel MUST validate runtime gateway host inputs before command construction and reject malformed or unsafe values.

#### Scenario: Host contains command metacharacters
- **WHEN** a gateway start request contains host text with shell metacharacters or invalid hostname/IP syntax
- **THEN** the request is rejected with validation error and no runtime command is executed

### Requirement: IPC Background Scan SHALL Not Block Event Loop
Periodic IPC auto-scan execution MUST run outside the main event loop blocking path.

#### Scenario: Auto-scan tick runs under load
- **WHEN** periodic scan processes large pending directories
- **THEN** the main event loop remains responsive to health endpoint requests

### Requirement: Form Transition Conflicts SHALL Be Deterministic
Concurrent transition writes against the same form instance MUST resolve as one success and explicit conflict for stale writers.

#### Scenario: Competing transitions for same form
- **WHEN** two transition operations race against the same current snapshot version
- **THEN** only one transition commits and the stale writer receives a deterministic conflict result

### Requirement: Startup SHALL Enforce Alembic Revision Governance
Application startup MUST fail when database schema revision is behind current Alembic head.

#### Scenario: Database revision is outdated
- **WHEN** app starts against an unmigrated database
- **THEN** startup fails with explicit guidance to run Alembic upgrade

