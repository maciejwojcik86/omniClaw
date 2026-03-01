# governance-bootstrap Specification

## Purpose
Define persistent governance rules for OmniClaw execution, including source precedence, OpenSpec workflow enforcement, task tracking contracts, and repository map maintenance.
## Requirements
### Requirement: Governance Baseline SHALL Be Defined in AGENTS
The project SHALL define a persistent governance baseline in `AGENTS.md` that captures mission, workflow contracts, source precedence, scope guardrails, and quality gates for all development work.

#### Scenario: Agent starts a new session
- **WHEN** an agent begins work on OmniClaw
- **THEN** the agent can read `AGENTS.md` and find explicit instructions for mission, workflow, and completion criteria

### Requirement: Canonical Source Order SHALL Be Explicit
The governance baseline SHALL define canonical source precedence as: `docs/current-task.md`, then `docs/master-task-list.md`, then active `openspec/changes/<id>/` artifacts, then PRD and roadmap documents.

#### Scenario: Conflicting instructions exist
- **WHEN** instructions conflict across planning and implementation documents
- **THEN** the agent resolves conflict using the canonical source order in `AGENTS.md`

### Requirement: Task Tracking Artifacts SHALL Exist
The repository SHALL contain `docs/master-task-list.md` and `docs/current-task.md` with stable structures that support milestone-level planning and single-change execution.

#### Scenario: Planning state is reviewed
- **WHEN** a developer opens task tracking documents
- **THEN** they can identify the active change, backlog milestones, dependencies, and acceptance checks

### Requirement: OpenSpec Workflow Contract SHALL Be Enforced
The governance baseline SHALL require the sequence `new change -> proposal -> specs -> design -> tasks -> implement -> validate -> archive` for each milestone change.

#### Scenario: New milestone starts
- **WHEN** work begins on a milestone
- **THEN** the corresponding `openspec/changes/<change-id>/` artifacts are created before implementation begins

### Requirement: Repository Map SHALL Be Maintained
The governance baseline SHALL include a repository map and mandate updating it after each completed change and after any structural/schema/API modification.

#### Scenario: Change modifies repository structure
- **WHEN** a change adds or reorganizes key files/folders
- **THEN** the repository map in `AGENTS.md` is updated in the same change
