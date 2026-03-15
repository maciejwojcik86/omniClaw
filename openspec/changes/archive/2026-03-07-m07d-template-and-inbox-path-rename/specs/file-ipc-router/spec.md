## MODIFIED Requirements

### Requirement: IPC Router SHALL Route MESSAGE Forms Between Node Workspaces
The kernel SHALL scan outbound message queue files and route valid `MESSAGE` Markdown forms from sender outbox to target inbox within the configured routing window.

#### Scenario: Valid message routed to destination inbox
- **WHEN** a node places a valid `MESSAGE` markdown file in its outbound send queue
- **THEN** the kernel routes the file to the destination node `inbox/new` path and records routing success metadata

### Requirement: Router Filesystem Lifecycle SHALL Be Deterministic
The router SHALL apply deterministic file transitions for routed and undelivered outcomes.

#### Scenario: Failed delivery transitions to dead-letter and feedback
- **WHEN** a routed form fails validation or holder resolution
- **THEN** sender-side source file transitions from pending queue to dead-letter path
- **AND** no destination payload is delivered as a normal message
- **AND** a kernel-authored feedback artifact is delivered to target `inbox/new` or sender `inbox/new` fallback
