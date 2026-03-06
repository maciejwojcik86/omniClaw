## 1. Schema and Service Contract

- [x] 1.1 Add Alembic, model, and repository changes for generic runtime config metadata and AGENT rows that no longer require per-agent Linux-user fields.
- [x] 1.2 Update settings and path-resolution helpers so canonical AGENT defaults resolve under `workspace/agents/<agent_name>/` with a sibling Nanobot `config.json`.
- [x] 1.3 Rework provisioning schemas, service logic, and adapters so `provision_agent` scaffolds repo-local Nanobot agent directories instead of creating Unix users.

## 2. Runtime and Deployment Assets

- [x] 2.1 Retarget runtime service and helper scripts to Nanobot start/stop/status execution using canonical config/workspace inputs and existing pid/log tracking.
- [x] 2.2 Rewrite Nanobot deployment assets under `scripts/provisioning/` and `workspace/forms/deploy_new_agent/skills/deploy-new-nanobot/` against the verified `/home/macos/.nanobot/` config/workspace baseline.
- [x] 2.3 Switch canonical deploy workflow assets to `deploy-new-nanobot` and keep `deploy-new-claw-agent` available as a legacy optional path without being the default stage skill.

## 3. Verification and Closure

- [x] 3.1 Update automated tests and smoke tooling for Nanobot paths, config schema, runtime behavior, and deploy workflow semantics.
- [x] 3.2 Update `docs/current-task.md`, `docs/plan.md`, `docs/documentation.md`, `docs/prompt.md`, `AGENTS.md`, and relevant runtime/deployment reference docs to reflect Nanobot as the canonical runtime.
- [x] 3.3 Run `uv run pytest -q` and `openspec validate --type change m07b-nanobot-runtime-migration --strict`.
- [x] 3.4 Complete Skill Delta Review: update existing skills or create focused Nanobot skills, refresh helper script references/command cheatsheets, and record reusable migration SOPs in the same change.
