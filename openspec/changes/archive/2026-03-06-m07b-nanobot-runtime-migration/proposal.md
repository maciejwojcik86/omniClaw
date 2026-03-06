## Why

OmniClaw's current agent contract is built around Nullclaw plus one Linux user per agent, but the project is now standardizing on Nanobot and its native multi-bot model. Keeping per-agent Unix users, `~/.nullclaw` paths, and cross-user runtime control would preserve complexity that Nanobot removes and would make future workflow automation harder to maintain.

## What Changes

- **BREAKING** Replace Nullclaw as the default agent runtime with Nanobot across provisioning, runtime control, workflow assets, tests, and operator documentation.
- **BREAKING** Change AGENT provisioning from Linux-user bootstrap to repo-local agent-folder creation under `<repo-root>/workspace/agents/<agent_name>/`, with each agent holding its own `config.json` and Nanobot workspace subtree.
- Preserve HUMAN registration for the kernel-running user, but stop requiring AGENT nodes to own a distinct OS user, home directory, or per-user binary link.
- Update canonical node metadata, runtime command templates, and migration logic away from `nullclaw_config_path` and Linux-user launch assumptions toward explicit Nanobot config/workspace inputs.
- Switch the canonical `deploy_new_agent` deployment stage from `deploy-new-claw-agent` to `deploy-new-nanobot`, while retaining the original Nullclaw skill package for optional/manual compatibility.
- Refresh docs, local skills, helper scripts, and smoke validation against the Nanobot reference layout under `/home/macos/.nanobot/`.

In scope:
- AGENT provisioning/runtime metadata and APIs.
- Deploy workflow and stage-skill migration to Nanobot.
- Database migration, scripts, tests, docs, and trackers needed for the Nanobot pivot.

Out of scope:
- Budgeting, context injection, and unrelated workflow feature work.
- Removing archived historical Nullclaw artifacts from past OpenSpec changes.
- Introducing a new isolation mechanism to replace per-agent Linux users in this change.

## Capabilities

### New Capabilities
- `deploy-new-agent-workflow`: Canonical `deploy_new_agent` workflow uses Nanobot deployment assets and the repo-local agent-folder workspace layout.

### Modified Capabilities
- `linux-provisioning`: AGENT provisioning changes from Linux-user bootstrap to Nanobot workspace/config scaffolding, while HUMAN registration remains supported.
- `agent-runtime-bootstrap`: Runtime control changes from Nullclaw-under-user execution to Nanobot launch/status management using explicit config/workspace inputs.

## Impact

- Core code and schema: `src/omniclaw/config.py`, `src/omniclaw/runtime/*`, `src/omniclaw/provisioning/*`, `src/omniclaw/db/*`, and new Alembic migration(s).
- Operator scripts: `scripts/provisioning/*`, `scripts/runtime/*`, and deploy smoke tooling under `scripts/forms/`.
- Workflow assets: `workspace/forms/deploy_new_agent/workflow.json` and stage-skill packages under `workspace/forms/deploy_new_agent/skills/`.
- Copied Nanobot skill package: `workspace/forms/deploy_new_agent/skills/deploy-new-nanobot/*`, which still carries Nullclaw naming/content and must be normalized.
- Test coverage: `tests/test_provisioning_actions.py`, `tests/test_runtime_actions.py`, `tests/test_forms_actions.py`, `tests/test_ipc_actions.py`, and schema assertions.
- Governance/docs: `AGENTS.md`, `docs/current-task.md`, `docs/plan.md`, `docs/documentation.md`, `docs/prompt.md`, and runtime/deployment reference skills.
