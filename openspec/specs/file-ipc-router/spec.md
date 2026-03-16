# file-ipc-router Specification

## Purpose
Define deterministic file-based MESSAGE routing between OmniClaw node workspaces with minimal frontmatter, flexible target addressing, and canonical lifecycle tracking in `forms_ledger`.
## Requirements
### Requirement: IPC Router SHALL Route MESSAGE Forms Between Node Workspaces
The kernel SHALL scan outbound message queue files and route valid `MESSAGE` Markdown forms from sender outbox to target inbox within the configured routing window.

#### Scenario: Valid message routed to destination inbox
- **WHEN** a node places a valid `MESSAGE` markdown file in its outbound send queue
- **THEN** the kernel routes the file to the destination node `inbox/new` path and records routing success metadata

### Requirement: IPC Router SHALL Resolve Form Package And Archive Roots From The Selected Company Workspace
The IPC router SHALL load active workflow packages from the selected company workspace forms root and SHALL write archive copies to the selected company workspace archive root.

#### Scenario: Router loads active workflow package
- **WHEN** the router or forms service needs a workflow definition or stage skill package
- **THEN** it resolves those assets from `<company-workspace-root>/forms/`
- **AND** it does not depend on `<repo-root>/workspace/forms/`

#### Scenario: Router writes archive copy
- **WHEN** a routed form is archived successfully
- **THEN** the archive copy is written under the selected company workspace archive root
- **AND** the sender and holder workspace transitions still use canonical node workspace paths

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

#### Scenario: Failed delivery transitions to dead-letter and feedback
- **WHEN** a routed form fails validation or holder resolution
- **THEN** sender-side source file transitions from pending queue to dead-letter path
- **AND** no destination payload is delivered as a normal message
- **AND** a kernel-authored feedback artifact is delivered to target `inbox/new` or sender `inbox/new` fallback

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

### Requirement: IPC Scan SHALL Refresh Active Agent Instructions Before Routing
Each IPC scan cycle SHALL refresh rendered `AGENTS.md` files and approved workspace `skills/` contents for active AGENT nodes before processing queued outbound forms.

#### Scenario: Manual scan refreshes instructions and approved skills
- **WHEN** an operator triggers an IPC scan action
- **THEN** the kernel performs the AGENT instruction render sweep before processing queued form files
- **AND** reconciles each active AGENT workspace `skills/` directory from approved skill assignments in the same pre-pass

#### Scenario: Background auto-scan refreshes instructions and approved skills
- **WHEN** the background IPC scan loop executes
- **THEN** the same render-and-skill reconciliation sweep runs before queued form processing without requiring a separate scheduler

### Requirement: Instruction Render Failures SHALL Not Block Form Routing
Instruction render failures during an IPC scan MUST be reported separately and MUST NOT prevent queued-form routing for other nodes in the same scan cycle.

#### Scenario: One AGENT render fails during scan
- **WHEN** the scan encounters a render error for one AGENT template
- **THEN** the kernel keeps the last good `AGENTS.md` for that node
- **AND** continues processing queued form files for the rest of the scan cycle
