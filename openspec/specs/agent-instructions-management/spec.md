# agent-instructions-management Specification

## Purpose
TBD - created by archiving change m08-context-injector. Update Purpose after archive.
## Requirements
### Requirement: Kernel SHALL Manage External Agent Instruction Templates
The kernel SHALL store editable AGENT instruction templates outside deployed workspaces and expose actions to read, preview, update, and sync those templates for authorized operators.

#### Scenario: Authorized manager reads subordinate template
- **WHEN** an authorized actor requests the template for a manageable AGENT node
- **THEN** the kernel returns the external `AGENTS.md` template content and canonical template path for that node

#### Scenario: Authorized manager updates subordinate template
- **WHEN** an authorized actor submits replacement template content for a manageable AGENT node
- **THEN** the kernel validates the template, writes it to the node's external template root, and returns the rendered preview metadata for that node

### Requirement: Instruction Template Defaults SHALL Resolve From The Selected Company Workspace
The kernel SHALL derive default external instruction-template roots and default AGENTS template sources from the selected company workspace rather than from repo-local runtime assets.

#### Scenario: Provisioned agent receives default external template root
- **WHEN** the kernel needs to derive an instruction-template root for an AGENT without an explicit override
- **THEN** it resolves that root under `<company-workspace-root>/nanobots_instructions/<agent_name>/`

#### Scenario: Default AGENTS template source is resolved
- **WHEN** the kernel seeds or repairs a missing default AGENTS template
- **THEN** it loads the baseline template from `<company-workspace-root>/nanobot_workspace_templates/AGENTS.md`
- **AND** it does not depend on a repo-local `workspace/nanobot_workspace_templates/AGENTS.md` default

### Requirement: Instructions Access SHALL Follow Company-Configured Hierarchy Rules
The kernel SHALL continue to authorize instruction-management actions using the management hierarchy, and any manager-facing skill-management actions that specify an actor node SHALL use the same hierarchy scope policy.

#### Scenario: Manager skill actions follow the same scope rules
- **WHEN** a manager invokes skill assignment or removal actions with an actor node
- **THEN** the kernel authorizes the target agent using the same direct-children or descendant policy used for instruction management

#### Scenario: Manager-facing skills arrive through assignment-based reconciliation
- **WHEN** the kernel reconciles approved skills for a node with subordinates
- **THEN** manager-facing loose master skills assigned by policy or operator action are delivered through the shared assignment-based skill reconciliation path
- **AND** the kernel no longer depends on a hardcoded manager-skill copy loop

### Requirement: AGENTS Template Rendering SHALL Use Allowlisted Placeholders
The context injector SHALL resolve the existing instruction placeholders plus budget-awareness placeholders for each AGENT node, and SHALL reject unknown placeholders during preview or template update actions.

#### Scenario: Budget placeholders render successfully
- **WHEN** a template uses supported variables such as `{{budget.mode}}`, `{{budget.daily_inflow_usd}}`, `{{budget.rollover_reserve_usd}}`, `{{budget.remaining_usd}}`, `{{budget.review_required_notice}}`, and `{{budget.direct_team_summary}}`
- **THEN** the kernel returns rendered AGENTS content with live budget values resolved from canonical state

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
