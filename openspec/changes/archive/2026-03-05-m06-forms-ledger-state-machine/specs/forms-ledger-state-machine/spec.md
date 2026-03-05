## ADDED Requirements

### Requirement: Form Workflow Graph SHALL Define Valid Lifecycle Decisions
The kernel SHALL evaluate form decisions against the active form-type workflow graph and reject any decision that is not represented as an allowed edge.

#### Scenario: Valid decision edge is applied
- **WHEN** a form decision request matches an allowed `from_status -> to_status` edge in the active workflow graph
- **THEN** the kernel persists the decision and updates the form snapshot status

#### Scenario: Invalid decision edge is rejected
- **WHEN** a form decision request does not match any allowed edge in the active workflow graph
- **THEN** the kernel rejects the decision and persists no snapshot or history mutation

### Requirement: Form Decisions SHALL Enforce Deterministic Holder Ownership
Each persisted form snapshot SHALL reference zero or one current holder node, and every successful decision SHALL resolve holder ownership according to target workflow node holder rules.

#### Scenario: Decision resolves named next holder
- **WHEN** a target workflow node defines a valid holder strategy (`static_node`, `static_node_name`, `field_ref`, `previous_holder`, `previous_actor`) and the referenced node resolves
- **THEN** the kernel updates the form snapshot with that single holder node

#### Scenario: Terminal decision clears holder
- **WHEN** a target workflow node uses `holder.strategy: none`
- **THEN** the kernel persists the new status with `current_holder_node` set to `null`

#### Scenario: Decision with invalid holder resolution is rejected
- **WHEN** a non-terminal decision request cannot resolve a valid next holder
- **THEN** the kernel rejects the decision and records a validation failure outcome

### Requirement: Form Instance IDs SHALL Be Deterministic
The kernel SHALL generate deterministic form instance IDs from form type and creation context, with deterministic collision handling.

#### Scenario: New form gets deterministic ID
- **WHEN** a new form instance is created from a form type definition
- **THEN** the generated `form_id` is stable for the same normalized creation context

#### Scenario: Deterministic collision suffix is applied
- **WHEN** a generated `form_id` already exists
- **THEN** the kernel applies a deterministic collision suffix policy and persists a unique ID

### Requirement: Form Decision History SHALL Be Append-Only
The kernel SHALL persist form lifecycle history as append-only decision events and SHALL NOT mutate or delete prior decision events during normal processing.

#### Scenario: Decision appends history event
- **WHEN** a form decision succeeds
- **THEN** a new decision event record is appended with prior/new status, holder, actor, and timestamp

#### Scenario: Existing history remains unchanged
- **WHEN** later decisions occur for the same form
- **THEN** previously stored decision events remain unchanged and queryable in original order

### Requirement: Workflow Decisions SHALL Support Branching Paths
Workflow graph edges SHALL support decision-key based branching so one source status can route to multiple target statuses.

#### Scenario: Decision routes to approval branch
- **WHEN** a decision request from a review status includes an `approve` decision key
- **THEN** the kernel follows the workflow edge mapped to the approval branch target status

#### Scenario: Decision routes to revision branch
- **WHEN** a decision request from the same review status includes a `request_changes` decision key
- **THEN** the kernel follows the workflow edge mapped to the revision branch target status
