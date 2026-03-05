## ADDED Requirements
> Legacy archive note: this historical M05 spec retains original router/filesystem "transitions" wording for traceability.

### Requirement: IPC Router SHALL Route MESSAGE Forms Between Node Workspaces
The kernel SHALL scan outbound message queue files and route valid `MESSAGE` Markdown forms from sender outbox to target inbox within the configured routing window.

#### Scenario: Valid message routed to destination inbox
- **WHEN** a node places a valid `MESSAGE` markdown file in its outbound send queue
- **THEN** the kernel routes the file to the destination node `inbox/unread` path and records routing success metadata

### Requirement: MESSAGE Frontmatter SHALL Use Minimal Contract
The router SHALL require a minimal frontmatter contract for `MESSAGE` forms and reject files that do not satisfy it.

#### Scenario: Valid minimal frontmatter
- **WHEN** a queued file frontmatter includes `type: MESSAGE`, `target`, `subject`, and `name`
- **THEN** the router accepts the file for permission checks and delivery processing

#### Scenario: Invalid or missing frontmatter fields
- **WHEN** a queued file omits required `MESSAGE` frontmatter keys or has invalid values
- **THEN** the router marks the message as dead-letter and records validation failure metadata

### Requirement: Sender Identity SHALL Be Derived From Canonical Workspace Mapping
The router SHALL derive sender identity from the source workspace node mapping rather than trusting frontmatter sender fields.

#### Scenario: Sender inferred from outbox ownership
- **WHEN** a queued message file is discovered in a node workspace outbox
- **THEN** sender node identity is resolved from canonical DB workspace mapping and persisted in routing records

### Requirement: IPC Router SHALL Enforce Hierarchy-Based Permission Checks
The router SHALL enforce routing permissions before delivering a message.

#### Scenario: Authorized message route
- **WHEN** sender and target satisfy configured hierarchy routing policy
- **THEN** the message is routed and delivery status is persisted as successful

#### Scenario: Unauthorized message route
- **WHEN** sender and target do not satisfy hierarchy routing policy
- **THEN** the message is not delivered, is moved to dead-letter handling, and failure reason is persisted

### Requirement: Message Lifecycle SHALL Be Persisted In Canonical DB
The kernel SHALL persist each processed `MESSAGE` file with lifecycle status and kernel-generated metadata beyond frontmatter values.

#### Scenario: Message routed successfully
- **WHEN** a `MESSAGE` file is delivered
- **THEN** DB state includes form type, lifecycle status, sender node, target node, subject, source path, delivery path, and routing timestamps

#### Scenario: Message routing fails
- **WHEN** a `MESSAGE` file fails validation or permission checks
- **THEN** DB state includes failure status, sender (when resolvable), target (when resolvable), and failure reason metadata

### Requirement: Router Filesystem Lifecycle SHALL Be Deterministic
The router SHALL apply deterministic file transitions for sent and archived/dead-letter outcomes.

#### Scenario: Successful delivery transitions to archive
- **WHEN** message routing succeeds
- **THEN** sender-side message file transitions from send queue to archive path while a delivered copy exists in destination inbox

#### Scenario: Failed delivery transitions to dead-letter
- **WHEN** message routing fails
- **THEN** sender-side message file transitions to dead-letter path and is not copied to destination inbox

### Requirement: Kernel SHALL Provide Deterministic Router Scan Control
The kernel SHALL expose an execution control path for router scans so tests and operators can trigger deterministic routing cycles.

#### Scenario: On-demand scan cycle
- **WHEN** an IPC router scan action is triggered
- **THEN** the kernel processes pending message files and returns a structured summary of routed and failed items
