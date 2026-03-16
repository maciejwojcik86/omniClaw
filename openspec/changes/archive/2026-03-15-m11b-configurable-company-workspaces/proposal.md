## Why

OmniClaw currently treats `<repo-root>/workspace/` as the one implicit company workspace, which couples company runtime state to a source checkout, mixes business assets into git-visible paths, and blocks clean operation across multiple companies. Now that forms, master skills, templates, archives, and the SQLite database are central runtime assets, the kernel needs a first-class configurable company workspace outside the repo.

## What Changes

- Introduce a configurable company workspace root, defaulting outside the repo at `<user-home>/.omniClaw/workspace`, with explicit startup/settings overrides for company workspace root, company config path, and database URL.
- Define a canonical company workspace layout for company-owned runtime assets: agents, active forms, active master skills, instruction templates, Nanobot workspace templates, model catalog assets, SQLite database, company `config.json`, activity logs, form archives, and retired/discontinued skill and form assets.
- Refactor kernel services and packaged scripts to resolve company-owned paths from the selected company workspace instead of hardcoding `<repo-root>/workspace/...`.
- Add bootstrap and migration tooling so operators can initialize a fresh company workspace or migrate an existing repo-local workspace into the new external layout.
- **BREAKING**: the implicit repo-local `./workspace` default is replaced by an external company workspace default; repo-local workspaces remain possible only through explicit configuration or migration tooling.

## Capabilities

### New Capabilities
- `company-workspace-management`: Select, derive, scaffold, and migrate a company workspace root that owns all company runtime assets outside the repo by default.

### Modified Capabilities
- `agent-runtime-bootstrap`: HUMAN supervisor defaults and bootstrap paths must derive from the selected company workspace instead of repo-local workspace defaults.
- `linux-provisioning`: Default AGENT paths, template roots, instruction-template roots, and company config resolution must derive from the selected company workspace.
- `deploy-new-agent-workflow`: The deploy workflow must provision new agents under the selected company workspace instead of `<repo-root>/workspace/agents/...`.
- `master-skill-lifecycle`: Active and retired company skill roots must derive from the selected company workspace, and active catalog scans must ignore retired/discontinued roots.
- `file-ipc-router`: Workflow package discovery and archive-copy output paths must derive from the selected company workspace.
- `agent-instructions-management`: Default external instruction-template roots and default AGENTS template sources must derive from the selected company workspace.

## Impact

- Affected code: `src/omniclaw/config.py`, `main.py`, `src/omniclaw/app.py`, provisioning/runtime/forms/ipc/instructions/skills/budgets services, DB session defaults, and company-facing scripts under `scripts/`.
- Affected runtime assets: company config file naming, SQLite database default location, company form/skill/template/archive roots, and local-stack startup assumptions.
- Affected docs/specs/tests: tracker docs, implementation docs, repository map, OpenSpec capability specs, path-heavy integration tests, and new workspace bootstrap/migration SOPs.
