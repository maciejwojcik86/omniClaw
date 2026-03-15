# ipc-invalid-feedback-routing Specification

## Purpose
TBD - created by archiving change ipc-invalid-feedback-and-dedupe. Update Purpose after archive.
## Requirements
### Requirement: Invalid IPC Files SHALL Be Dead-Lettered Once
The kernel MUST move invalid queued form files from sender pending queue to sender dead-letter path during the same scan cycle that detects failure.

#### Scenario: Validation failure dead-letters source file
- **WHEN** queued form fails frontmatter, workflow, or resolution validation
- **THEN** source file is moved to sender `outbox/dead-letter` and is not reprocessed in subsequent scans unless explicitly requeued

### Requirement: Kernel SHALL Emit Structured Feedback Artifact
The kernel MUST generate a feedback markdown artifact for undelivered files with structured YAML error fields.

#### Scenario: Feedback artifact contains structured fields
- **WHEN** form is marked undelivered
- **THEN** feedback frontmatter includes `error_code`, `error_message`, `invalid_field`, `original_source_path`, `original_target`, `original_stage`, and `original_decision`

### Requirement: Feedback Delivery SHALL Use Target-First With Sender Fallback
Feedback routing MUST use resolved target inbox when possible and sender inbox when target resolution fails.

#### Scenario: Target resolves
- **WHEN** undelivered form has resolvable target node workspace
- **THEN** feedback artifact is delivered to target `inbox/new`

#### Scenario: Target unresolved
- **WHEN** undelivered form target cannot be resolved
- **THEN** feedback artifact is delivered to sender `inbox/new`

### Requirement: Requeue SHALL Be Explicit Operator Action
The project MUST provide helper tooling to move dead-letter files back to pending queue intentionally.

#### Scenario: Operator requeues dead-letter file
- **WHEN** requeue helper is run for selected dead-letter file
- **THEN** file is moved to sender pending queue with collision-safe naming and becomes eligible for next scan
