## MODIFIED Requirements

### Requirement: MESSAGE Frontmatter SHALL Use Minimal Contract
The router SHALL require a minimal frontmatter contract for `MESSAGE` forms and reject files that do not satisfy it.

#### Scenario: Valid minimal frontmatter
- **WHEN** a queued file frontmatter includes `type: MESSAGE`, `sender`, `target`, and `subject`
- **THEN** the router accepts the file for permission checks and delivery processing

#### Scenario: Invalid or missing frontmatter fields
- **WHEN** a queued file omits required `MESSAGE` frontmatter keys or has invalid values
- **THEN** the router marks the message as undelivered, moves source file to sender dead-letter path, and returns validation failure metadata including feedback delivery path

### Requirement: Router Filesystem Lifecycle SHALL Be Deterministic
The router SHALL apply deterministic file transitions for routed and undelivered outcomes.

#### Scenario: Successful delivery transitions to archive
- **WHEN** message routing succeeds
- **THEN** sender-side message file transitions from send queue to archive path while a delivered copy exists in destination inbox

#### Scenario: Failed delivery transitions to dead-letter and feedback
- **WHEN** message routing fails
- **THEN** sender-side source file transitions from pending queue to dead-letter path, no destination payload is delivered as normal message, and a kernel-authored feedback artifact is delivered to target inbox (or sender inbox fallback)

## ADDED Requirements

### Requirement: IPC Undelivered Response SHALL Include Dead-Letter and Feedback Paths
The scan response MUST include deterministic filesystem paths for dead-lettered source and generated feedback artifacts.

#### Scenario: Undelivered item response contract
- **WHEN** scan returns undelivered item
- **THEN** item metadata includes `dead_letter_path` and `feedback_path` fields alongside failure reason
