## ADDED Requirements

### Requirement: Kernel SHALL Manage External Agent Instruction Templates
The kernel SHALL store editable AGENT instruction templates outside deployed workspaces and expose actions to read, preview, update, and sync those templates for authorized operators.

#### Scenario: Authorized manager reads subordinate template
- **WHEN** an authorized actor requests the template for a manageable AGENT node
- **THEN** the kernel returns the external `AGENTS.md` template content and canonical template path for that node

#### Scenario: Authorized manager updates subordinate template
- **WHEN** an authorized actor submits replacement template content for a manageable AGENT node
- **THEN** the kernel validates the template, writes it to the node's external template root, and returns the rendered preview metadata for that node

### Requirement: Instructions Access SHALL Follow Company-Configured Hierarchy Rules
The kernel SHALL authorize instruction-management actions using the management hierarchy and a company-configured access scope of `direct_children` or `descendant`.

#### Scenario: Direct-children scope limits access
- **WHEN** company config sets `instructions.access_scope` to `direct_children`
- **THEN** an actor may manage only AGENT nodes directly linked as its children

#### Scenario: Descendant scope expands access
- **WHEN** company config sets `instructions.access_scope` to `descendant`
- **THEN** an actor may manage any AGENT node reachable below it in the hierarchy chain

### Requirement: AGENTS Template Rendering SHALL Use Allowlisted Placeholders
The context injector SHALL resolve only the supported placeholder set for M08 and SHALL reject unknown placeholders during preview or template update actions.

#### Scenario: Supported placeholders render successfully
- **WHEN** a template uses supported variables such as `{{node.name}}`, `{{node.role_name}}`, `{{manager.name}}`, `{{line_manager}}`, `{{subordinates_list}}`, `{{inbox_unread_summary}}`, and `{{current_time_utc}}`
- **THEN** the kernel returns rendered AGENTS content with live values resolved from canonical state and live inbox files

#### Scenario: Unknown placeholder is rejected
- **WHEN** a template includes an unsupported placeholder
- **THEN** preview and template update actions fail with validation details and do not replace the stored template

### Requirement: Rendered AGENTS SHALL Remain Kernel-Controlled Workspace Outputs
The kernel SHALL render final `AGENTS.md` files into deployed AGENT workspaces as read-only outputs derived from the external template source.

#### Scenario: Successful render writes workspace AGENTS
- **WHEN** the kernel syncs instructions for an AGENT node with a valid template
- **THEN** it overwrites the deployed workspace `AGENTS.md` with rendered content and resets the file to a read-only mode

#### Scenario: Render failure preserves last good AGENTS
- **WHEN** a sync attempt encounters a rendering error for an AGENT node
- **THEN** the previously rendered workspace `AGENTS.md` remains unchanged and the kernel reports the render failure

### Requirement: Kernel SHALL Summarize Live Unread Inbox Content For Templates
The context injector SHALL derive `{{inbox_unread_summary}}` from the live `inbox/new` filesystem for the target AGENT workspace.

#### Scenario: Unread inbox summary is rendered from live files
- **WHEN** an AGENT workspace contains unread markdown forms in `inbox/new`
- **THEN** the rendered summary lists each unread item with sender, form type, stage, and subject or filename fallback in short line form

#### Scenario: Empty unread inbox renders explicit empty state
- **WHEN** an AGENT workspace has no unread markdown forms
- **THEN** the rendered summary resolves to a deterministic empty-state string rather than stale historical delivery metadata
