## Context

The current kernel assumes one repo-local company workspace rooted at `<repo-root>/workspace/`. That assumption now spans:
- settings defaults such as `sqlite:///./workspace/omniclaw.db`
- company config resolution through `workspace/company_config.json`
- provisioning defaults for HUMAN and AGENT workspaces
- forms and skill discovery in services that hardcode `Path(__file__).resolve().parents[3] / "workspace" / ...`
- scripts that assume repo-local database, forms, archive, and agent roots

This creates three problems:
1. company runtime state lives inside the source repo and is awkward to keep out of git
2. all deployments implicitly share one company workspace unless operators manually override many pieces
3. new M11-managed company assets made the repo-local assumption broader, not smaller

The user goal is not true multi-tenant execution inside one kernel process. The immediate goal is to let operators run multiple isolated company environments by selecting different company workspaces and config/database paths at startup.

## Goals / Non-Goals

**Goals:**
- Make company runtime state resolve from one selected company workspace root.
- Default the company workspace outside the repo at `<user-home>/.omniClaw/workspace`.
- Derive company config (`config.json`) and SQLite database defaults from the selected workspace.
- Keep company-owned runtime assets out of the repo by default, while allowing explicit alternate roots.
- Provide a canonical workspace layout covering active assets, archives/logs, and retired/discontinued assets.
- Add bootstrap/migration tooling for new or existing company workspaces.
- Allow several company environments by launching OmniClaw with different workspace selections.

**Non-Goals:**
- Running multiple companies as tenants inside a single kernel process.
- Redesigning business workflows, budget logic, or skill lifecycle semantics beyond path/config resolution.
- Replacing per-node `workspace_root` and `runtime_config_path` canonical DB metadata.
- Introducing a new database engine; SQLite remains the default, now relocated under the company workspace.

## Decisions

### 1. One company workspace per kernel process

The kernel will resolve exactly one active company workspace per process start.

Why:
- This matches the current app model and keeps isolation deterministic.
- It avoids adding tenant IDs or cross-company authorization semantics throughout the DB and APIs.

Rejected alternative:
- True multi-tenant company support inside one process. Rejected because it would require tenant-aware schema, API auth boundaries, background-loop isolation, and migration complexity far beyond the path/config problem the user asked to solve.

### 2. Introduce a shared company-path resolver in settings/application bootstrap

The kernel should derive all company-owned paths from one resolver object built from settings:
- `company_workspace_root`
- `company_config_path`
- `database_url` default
- active and retired asset roots

Why:
- The repo currently has repeated per-service path joins against `<repo-root>/workspace`.
- Centralizing derivation makes tests, scripts, and future migrations deterministic.

Rejected alternative:
- Let each service continue to derive its own workspace paths from `company_config_path` or repo root. Rejected because it preserves drift and guarantees more path bugs.

### 3. Default layout stays path-compatible where possible

Inside the selected company workspace, active roots should keep familiar names where practical:
- `agents/`
- `forms/`
- `master_skills/`
- `nanobots_instructions/`
- `nanobot_workspace_templates/`
- `models/` or a model-catalog artifact
- `form_archive/`
- `logs/`
- `retired/forms/`
- `retired/master_skills/`
- `config.json`
- `omniclaw.db`

Why:
- This minimizes refactor churn and makes migration from the repo-local workspace straightforward.
- Existing scripts and services can be updated to use a new root without redesigning every subpath.

Rejected alternative:
- A completely new nested layout such as `active/forms`, `archive/forms`, `graveyard/forms`, etc. Rejected for now because it multiplies migration work without adding immediate operator value.

### 4. Company config file becomes `config.json`

The selected company workspace should use `<company-workspace-root>/config.json` as the default company settings file, replacing the repo-local `workspace/company_config.json` default.

Why:
- The user explicitly wants a company-owned config file in the company workspace.
- It aligns with a self-contained company folder that can be moved or duplicated as one unit.

Rejected alternative:
- Keep `company_config.json` as the default filename forever. Rejected because it preserves the old repo-local naming and is less aligned with the requested standalone company workspace contract.

### 5. Fresh installs default outside the repo, with migration tooling for existing repos

Fresh resolution defaults to `<user-home>/.omniClaw/workspace`. Existing repo-local installations are migrated with an explicit helper rather than silently auto-moving files.

Why:
- Silent relocation of company data is risky.
- Explicit migration keeps operator intent clear and makes rollback easier.

Rejected alternative:
- Auto-detect and silently move `<repo-root>/workspace` on startup. Rejected because it is too destructive and hard to reason about in a dirty worktree.

## Risks / Trade-offs

- [Default-path breakage] Existing scripts and local habits assume `./workspace` → Mitigation: add explicit overrides, migration tooling, and update canonical wrappers.
- [Partial migration state] Operators may copy only part of the old workspace → Mitigation: add scaffold validation and clear missing-root/config errors.
- [Path drift in services] Repo-root path joins exist across multiple modules → Mitigation: centralize company path derivation and cover it with focused tests.
- [Concurrent local stacks] Multiple company roots may still collide on ports or LiteLLM settings → Mitigation: treat per-company runtime port selection as operator-configured and document it clearly.
- [Config filename transition] `company_config.json` callers may break → Mitigation: support explicit override paths and migration docs during the transition window.

## Migration Plan

1. Add settings/CLI support for selecting `company_workspace_root`, `company_config_path`, and derived default SQLite path.
2. Introduce a shared company-path resolver and convert services/scripts away from repo-root `workspace` joins.
3. Add workspace-init tooling to scaffold the expected directories and baseline `config.json`.
4. Add migration tooling to copy or move existing repo-local workspace assets into the selected external company workspace.
5. Update tests, docs, and local-stack helpers to use the selected company workspace explicitly.
6. Rollback path: point the kernel back at the previous repo-local workspace explicitly if migration or new-path rollout fails.

## Open Questions

- Should the model catalog be a directory (`models/`) or a single file (`models.json`) in this change?
- Should `company_config.json` remain as a compatibility alias for one release window, or should the migration helper rewrite to `config.json` immediately?
- Do we want a dedicated API or script to report the currently selected company workspace and derived paths for operator debugging?
- Should retired/discontinued form and skill assets be moved automatically by lifecycle actions in this change, or should this change only create and reserve those roots?
