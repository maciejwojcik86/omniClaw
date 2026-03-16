## ADDED Requirements

### Requirement: Kernel SHALL Catalog All Agent-Visible Master Skills
The kernel SHALL maintain one canonical master-skill catalog for both loose company skills and form-linked stage skills, storing each skill's name, lifecycle status, source path, description, version, and optional owning form type.

#### Scenario: Loose company skill is cataloged
- **WHEN** an operator drafts or updates a loose company skill through the skills API
- **THEN** the kernel records the skill in the master-skill catalog with `form_type_key = null`
- **AND** persists the canonical source path under the company master-skill workspace

#### Scenario: Form-linked skill is cataloged
- **WHEN** a workflow package with stage skills is activated or synced from workspace assets
- **THEN** the kernel records each referenced stage skill in the same catalog
- **AND** persists the skill source path from the form package with the owning `form_type_key`

### Requirement: Loose Master Skills SHALL Support Draft Activation And Deactivation
Loose company master skills SHALL expose a lifecycle of `DRAFT`, `ACTIVE`, and `DEACTIVATED`, and only `ACTIVE` loose skills SHALL be eligible for manual assignment to agents.

#### Scenario: Draft loose skill cannot be assigned
- **WHEN** an operator attempts to manually assign a loose company skill whose lifecycle is `DRAFT`
- **THEN** the kernel rejects the assignment request
- **AND** reports that only active loose skills are manually assignable

#### Scenario: Active loose skill can be deactivated
- **WHEN** an operator changes a loose company skill lifecycle to `DEACTIVATED`
- **THEN** future manual assignments of that skill are rejected
- **AND** existing assignments remain visible to reconciliation until explicitly removed or superseded by policy

### Requirement: Kernel SHALL Provide Batch Skill Assignment Actions
The kernel SHALL expose actions to list master skills, list active loose skills, list agent assignments, assign multiple loose skills to an agent, remove multiple loose skills from an agent, and trigger on-demand reconciliation.

#### Scenario: Operator assigns multiple loose skills
- **WHEN** an operator submits an `assign_master_skills` request with multiple skill names for an AGENT
- **THEN** the kernel records manual assignment rows for every valid active loose skill in the request
- **AND** returns the effective assignment state for the target agent

#### Scenario: Assignment list reports effective skill sources
- **WHEN** an operator requests `list_agent_skill_assignments`
- **THEN** the kernel returns the target agent's assigned skills
- **AND** identifies whether each assignment came from `MANUAL`, `DEFAULT`, or `FORM_STAGE`

### Requirement: Manager-Scoped Assignment Actions SHALL Follow Hierarchy Authorization
When skill assignment actions include an actor node, the kernel SHALL authorize target-agent access using the same company hierarchy policy used for managed instructions.

#### Scenario: Manager assigns skills to descendant agent
- **WHEN** an authorized manager submits `assign_master_skills` for an agent inside the allowed management scope
- **THEN** the kernel applies the assignment request

#### Scenario: Manager cannot assign skills outside hierarchy
- **WHEN** a manager submits `remove_master_skills` for an AGENT outside the allowed management scope
- **THEN** the kernel rejects the request with an authorization error

### Requirement: Skill Reconciliation SHALL Rebuild Agent Workspace Skills From Approved Assignments
The kernel SHALL reconcile each agent workspace `skills/` directory by removing unapproved contents and rebuilding it from the catalog entries referenced by the agent's current assignments.

#### Scenario: Stray local skill is removed during reconciliation
- **WHEN** an agent workspace contains a skill folder that is not present in the current approved assignment set
- **THEN** the kernel deletes that stray folder during reconciliation
- **AND** leaves only approved skill packages in the workspace `skills/` directory

#### Scenario: Approved skills are restored from catalog paths
- **WHEN** reconciliation runs for an AGENT with manual, default, and form-stage assignments
- **THEN** the kernel copies every approved skill package from its canonical catalog source path
- **AND** normalizes the deployed `skill.json` metadata inside the rebuilt workspace skill folders
