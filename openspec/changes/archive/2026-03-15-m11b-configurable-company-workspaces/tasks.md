## 1. OpenSpec And Tracker Alignment

- [x] 1.1 Update `docs/current-task.md`, `docs/plan.md`, and `docs/implement.md` so `m11b-configurable-company-workspaces` is the active change and `m11-master-skill-lifecycle` is recorded as archived.
- [x] 1.2 Update living documentation and repository map entries to reflect the planned shift from repo-local company assets to a selected external company workspace.

## 2. Settings And Company Path Resolution

- [x] 2.1 Extend settings and startup entrypoints to accept company workspace root and company config overrides, and derive default `config.json` and SQLite paths from the selected workspace root.
- [x] 2.2 Add a shared company-path resolver/model so services and scripts stop hardcoding `<repo-root>/workspace/...` joins.

## 3. Kernel Service And Script Integration

- [x] 3.1 Update provisioning, runtime, instructions, forms, IPC, skills, budgets, and DB/session defaults to use the resolved company workspace paths.
- [x] 3.2 Update canonical scripts and local stack helpers to accept or propagate the selected company workspace, config, and database inputs consistently.

## 4. Workspace Scaffold And Migration

- [x] 4.1 Add company-workspace bootstrap tooling to scaffold active, archive/log, and retired/discontinued directories plus a baseline `config.json`.
- [x] 4.2 Add migration tooling and validation to move or copy an existing repo-local workspace into a selected external company workspace with clear reporting.

## 5. Verification And Skill Capture

- [x] 5.1 Add or update tests covering default home-directory workspace selection, explicit overrides, derived path usage across services, and isolation between two different company roots.
- [x] 5.2 Create or update mirrored developer/copilot skills for company-workspace bootstrap and migration, and refresh the relevant operator/developer docs.
- [x] 5.3 Run targeted validation, full pytest, and `openspec validate --type change m11b-configurable-company-workspaces --strict`.
