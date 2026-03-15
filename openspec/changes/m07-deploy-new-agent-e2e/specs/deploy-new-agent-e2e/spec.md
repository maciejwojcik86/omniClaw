## ADDED Requirements

### Requirement: Deploy-New-Agent Workflow SHALL Complete Deterministic IPC Stage Cycle
The kernel routing stack MUST support deterministic `deploy_new_agent` stage progression across approval and deployment stages through terminal archive.

#### Scenario: Macos-originated request traverses all stages
- **WHEN** a `deploy_new_agent` form is submitted from `workspace/macos/outbox/send`
- **THEN** IPC processing routes the form through `BUSINESS_CASE -> HR_REVIEW -> FINANCE_REVIEW -> DIRECTOR_APPROVAL -> AGENT_DEPLOYMENT -> ARCHIVED` according to decisions and target rules

#### Scenario: Terminal archive after deploy-and-archive
- **WHEN** `AGENT_DEPLOYMENT` holder submits decision `deploy_and_archive`
- **THEN** form transitions to terminal `ARCHIVED`, no holder delivery copy is created, and archive/backup copies are persisted deterministically

### Requirement: Deploy-New-Agent Validation Assets SHALL Cover Preflight and Route-Time Skill Readiness
M07 operator tooling MUST provide preflight checks and route-time verification for workflow participants and required skill packages.

#### Scenario: Preflight validates participant readiness
- **WHEN** operator starts deploy workflow smoke script
- **THEN** script verifies required nodes/workspaces exist and required baseline files (`AGENTS.md`, `HEARTBEAT.md`) are present for configured participants

#### Scenario: Route-time skill package availability is verified
- **WHEN** each stage transition is routed
- **THEN** required stage skill package existence is verified for expected holder paths under `<workspace>/skills/<required_skill>/`
