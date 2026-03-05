# file-ipc-router Specification

## Purpose
Define deterministic file-based MESSAGE routing between OmniClaw node workspaces with minimal frontmatter, flexible target addressing, and canonical lifecycle tracking in `forms_ledger`.
## Requirements
### Requirement: IPC Router SHALL Route MESSAGE Forms Between Node Workspaces
The kernel SHALL scan outbound message queue files and route valid `MESSAGE` Markdown forms from sender outbox to target inbox within the configured routing window.

#### Scenario: Valid message routed to destination inbox
- **WHEN** a node places a valid `MESSAGE` markdown file in its outbound send queue
- **THEN** the kernel routes the file to the destination node `inbox/unread` path and records routing success metadata

### Requirement: MESSAGE Frontmatter SHALL Use Minimal Contract
The router SHALL require a minimal frontmatter contract for `MESSAGE` forms and reject files that do not satisfy it.

#### Scenario: Valid minimal frontmatter
- **WHEN** a queued file frontmatter includes `type: MESSAGE`, `sender`, `target`, and `subject`
- **THEN** the router accepts the file for permission checks and delivery processing

#### Scenario: Invalid or missing frontmatter fields
- **WHEN** a queued file omits required `MESSAGE` frontmatter keys or has invalid values
- **THEN** the router marks the message as undelivered, moves source file to sender dead-letter path, and returns validation failure metadata including feedback delivery path

### Requirement: Sender Identity SHALL Be Derived From Canonical Workspace Mapping
The router SHALL derive sender identity from the source workspace node mapping rather than trusting frontmatter sender fields.

#### Scenario: Sender inferred from outbox ownership
- **WHEN** a queued message file is discovered in a node workspace outbox
- **THEN** sender node identity is resolved from canonical DB workspace mapping and persisted in routing records

### Requirement: IPC Router SHALL Route MESSAGE To Any Registered Target Node
The router SHALL allow MESSAGE delivery to any registered target node that resolves to a valid workspace.

#### Scenario: Target node exists with workspace
- **WHEN** sender submits a valid MESSAGE and target node exists with valid workspace paths
- **THEN** the message is routed and delivery status is persisted as successful

#### Scenario: Target node missing or unroutable
- **WHEN** target node cannot be resolved or has invalid workspace configuration
- **THEN** the message is not delivered, remains queued, and failure reason is returned

### Requirement: Message Lifecycle SHALL Be Persisted In Canonical DB
The kernel SHALL persist each processed `MESSAGE` file with lifecycle status and kernel-generated metadata beyond frontmatter values.

#### Scenario: Message routed successfully
- **WHEN** a `MESSAGE` file is delivered
- **THEN** DB state includes form type, lifecycle status, sender node, target node, subject, source path, delivery path, and routing timestamps

#### Scenario: Message routing fails
- **WHEN** a `MESSAGE` file fails validation or target resolution checks
- **THEN** DB state is unchanged for that file and failure reason metadata is returned in scan output

### Requirement: Router Filesystem Lifecycle SHALL Be Deterministic
The router SHALL apply deterministic file transitions for routed and undelivered outcomes.

#### Scenario: Successful delivery transitions to archive
- **WHEN** message routing succeeds
- **THEN** sender-side message file transitions from send queue to archive path while a delivered copy exists in destination inbox

#### Scenario: Failed delivery transitions to dead-letter and feedback
- **WHEN** message routing fails
- **THEN** sender-side source file transitions from pending queue to dead-letter path, no destination payload is delivered as normal message, and a kernel-authored feedback artifact is delivered to target inbox (or sender inbox fallback)

### Requirement: Kernel SHALL Provide Deterministic Router Scan Control
The kernel SHALL expose an execution control path for router scans so tests and operators can trigger deterministic routing cycles.

#### Scenario: On-demand scan cycle
- **WHEN** an IPC router scan action is triggered
- **THEN** the kernel processes pending message files and returns a structured summary of routed and undelivered items

### Requirement: IPC Scan SHALL Stop Processing After Requested Limit
The IPC router MUST stop queue traversal once the requested scan limit is reached.

#### Scenario: Limit reached in large queue
- **WHEN** scan is invoked with limit `N` and queue contains more than `N` files
- **THEN** no more than `N` eligible files are processed in that scan cycle

### Requirement: IPC Auto-Scan SHALL Run via Non-Blocking Execution Path
Kernel auto-scan loop MUST run filesystem scan work outside the asyncio event loop thread.

#### Scenario: Auto-scan enabled with high queue depth
- **WHEN** background scan executes repeatedly
- **THEN** health and control endpoints remain responsive while scan work runs

### Requirement: IPC Undelivered Response SHALL Include Dead-Letter and Feedback Paths
The scan response MUST include deterministic filesystem paths for dead-lettered source and generated feedback artifacts.

#### Scenario: Undelivered item response contract
- **WHEN** scan returns undelivered item
- **THEN** item metadata includes `dead_letter_path` and `feedback_path` fields alongside failure reason

