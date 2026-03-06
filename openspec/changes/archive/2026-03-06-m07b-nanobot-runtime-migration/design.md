## Context

OmniClaw currently treats an AGENT node as a Linux account plus a Nullclaw config/workspace pair. That assumption is spread across the `nodes` schema (`linux_*`, `nullclaw_config_path`, `gateway_*`), provisioning APIs (`create_linux_user`, `home_dir`, `manager_group`), runtime control (`sudo -u`, `nullclaw gateway`), deploy scripts, and operator skills.

The target runtime is now Nanobot. The verified local reference under `/home/macos/.nanobot/` shows:
- `config.json` centered on `agents.defaults.workspace`, `gateway`, and `tools.restrictToWorkspace`
- native workspace assets `AGENTS.md`, `HEARTBEAT.md`, `SOUL.md`, `TOOLS.md`, `USER.md`
- Nanobot-managed `memory/` and `sessions/` directories

The local CLI also confirms first-class `gateway`, `agent`, and `status` commands. Upstream documentation indicates multi-instance operation via explicit config/workspace inputs, but the installed CLI help does not expose those flags yet. That mismatch needs to be treated as a migration detail, not ignored.

## Goals / Non-Goals

**Goals:**
- Make Nanobot the canonical runtime for AGENT nodes.
- Replace per-agent Linux-user provisioning with repo-local agent directories under `workspace/agents/`.
- Keep `workspace_root` as the canonical IPC/forms root for each node.
- Preserve existing HUMAN registration and line-management semantics where they are still useful.
- Switch the canonical `deploy_new_agent` stage skill to `deploy-new-nanobot` while keeping the legacy Nullclaw skill available.
- Update tests, docs, and skills in the same change so Nullclaw assumptions stop reappearing.

**Non-Goals:**
- Re-architect IPC routing, form state transitions, or budgeting behavior.
- Introduce a new runtime session table unless Nanobot proves incompatible with one-process-per-agent tracking.
- Remove all archived Nullclaw history from old OpenSpec artifacts.
- Design a replacement security/isolation model beyond distinct agent folders and existing Nanobot workspace restrictions.

## Decisions

### 1. Canonical agent layout becomes `workspace/agents/<agent_name>/`

AGENT nodes will be provisioned into repo-local directories:
- `workspace/agents/<agent_name>/config.json`
- `workspace/agents/<agent_name>/workspace/`

`Node.workspace_root` will continue to point at the nested `workspace/` directory because IPC routing, form delivery, and skill distribution already depend on that contract. The sibling `config.json` path becomes runtime metadata.

Why:
- It matches the user-requested Nanobot layout.
- It preserves current router/forms assumptions with minimal churn.
- It cleanly separates Nanobot runtime config from OmniClaw message-routing folders.

Rejected alternative:
- Put `config.json` inside the workspace root. Rejected because it blurs runtime config with routed content and does not match the requested folder contract.

### 2. Runtime config metadata becomes generic; Linux-user metadata becomes optional for AGENT nodes

The schema should stop treating `nullclaw_config_path` as canonical. This change will migrate to a generic runtime config field (preferred: `runtime_config_path`) while leaving `linux_uid`, `linux_username`, and `linux_password` available for HUMAN nodes and legacy data.

For AGENT nodes:
- `workspace_root` remains required
- runtime config path becomes required
- Linux-user fields become optional/non-canonical

Why:
- The runtime vendor may change again; a generic config-path field avoids another schema rename.
- HUMAN registration still legitimately cares about the host Linux user.
- AGENT rows no longer need fake Unix-account data just to satisfy runtime launch code.

Rejected alternative:
- Introduce separate HUMAN and AGENT metadata tables now. Rejected because it expands migration scope far beyond the runtime pivot and is not required to get Nanobot working.

### 3. Keep the current runtime action surface, but retarget execution to Nanobot

`gateway_start`, `gateway_stop`, `gateway_status`, and `list_agents` stay in place. The runtime service will switch from `sudo -u <linux_username> nullclaw gateway ...` to a Nanobot-backed launch path that resolves the node's config/workspace metadata and records pid/log metadata the same way the current service does.

The current `gateway_*` fields on `nodes` remain in this change unless implementation proves Nanobot is not operable as one tracked process per AGENT node.

Why:
- The operator/API surface already exists and is tested.
- The local Nanobot binary exposes `gateway`, `agent`, and `status`, so a like-for-like runtime bridge is still plausible.
- This avoids an unnecessary control-plane redesign before the Nanobot contract is fully validated.

Rejected alternative:
- Replace gateway actions with a brand-new session/terminal model immediately. Rejected because the repository does not need that refactor yet, and the runtime CLI still presents a gateway command.

### 4. `provision_agent` remains the canonical API verb, but its behavior changes

The provisioning API will stay centered on `register_human` and `provision_agent`:
- `register_human` continues to support the kernel-running Linux user
- `provision_agent` becomes repo-local directory/config scaffolding plus DB upsert/linkage

Legacy Linux-user-shaped actions (`create_linux_user`, `apply_workspace_permissions`, sudo/grant scripts) may remain temporarily for compatibility or HUMAN-only/manual operations, but they stop being part of the canonical AGENT deployment path.

Why:
- Existing forms, scripts, and tests already know the `provision_agent` action.
- The business concept is still “deploy an agent”; only the implementation model changes.

Rejected alternative:
- Introduce a separate `provision_nanobot_agent` API action. Rejected because it would duplicate behavior and force broader workflow rewiring for little gain.

### 5. The copied `deploy-new-nanobot` package is treated as a rewrite target, not a ready asset

`workspace/forms/deploy_new_agent/skills/deploy-new-nanobot/` already exists, but it is only a folder rename and still declares `deploy-new-claw-agent`, forwards to `deploy_new_claw_agent.sh`, and documents `~/.nullclaw` paths. The change will not point the canonical workflow at that package until:
- skill metadata names are corrected
- scripts/templates are Nanobot-specific
- config templates are aligned to the verified `/home/macos/.nanobot/` baseline
- the operator copy under `workspace/macos/skills/` is updated consistently

Why:
- Switching the workflow before the package is real would create a broken stage skill.
- The form routing layer is already generic; the main risk is incorrect stage execution guidance.

Rejected alternative:
- Change `workflow.json` first and clean up the Nanobot skill later. Rejected because it would immediately break deploy-stage execution.

### 6. Keep the repo-local `workspace/` root in this change

This change will standardize AGENT folders under the existing repo-local `workspace/` tree rather than introducing a new top-level workspace-root configuration variable across forms, IPC, and documentation.

Why:
- Forms, archives, and workflow packages already assume `workspace/` under the repo.
- The runtime pivot is already cross-cutting; adding a global storage-root abstraction would widen scope without solving the core migration blocker.

Rejected alternative:
- Add a new authoritative workspace-root setting now. Rejected because the agent-directory migration can succeed under the existing repo-local root.

## Risks / Trade-offs

- [Nanobot CLI contract mismatch] Upstream docs indicate explicit config/workspace inputs, but local CLI help does not show the same flags. → Mitigation: validate the installed binary during implementation and introduce a wrapper script if the CLI requires env vars or different argument ordering.
- [Schema churn across the app] `nullclaw_config_path` and Linux-user assumptions appear in models, repository code, tests, scripts, and skills. → Mitigation: do one deliberate migration with compatibility-minded code updates and update verification scripts in the same slice.
- [Legacy Nullclaw assets keep reappearing] Authoring docs and copied skills currently teach `deploy-new-claw-agent`. → Mitigation: switch the canonical workflow, update authoring/operator docs, and label the legacy Nullclaw path as optional compatibility only.
- [Reduced OS-level isolation] Removing per-agent Unix users lowers one layer of host isolation. → Mitigation: keep distinct agent folders, preserve Nanobot `restrictToWorkspace`, and explicitly document that stronger isolation is deferred.
- [Existing live nodes still point to `/home/.../.nullclaw`] Director/HR/Ops dev assets may break if the DB is migrated without workspace reprovisioning. → Mitigation: include a migration/reseed step for local runtime assets and a smoke checklist for migrated nodes.

## Migration Plan

1. Add schema migration(s) for generic runtime config metadata and any AGENT-field optionality needed by the new model.
2. Update provisioning services/adapters so `provision_agent` scaffolds `workspace/agents/<agent_name>/` instead of creating a Unix user.
3. Update runtime config/service code to build Nanobot launch commands from canonical config/workspace metadata and keep pid/log tracking.
4. Rewrite the `deploy-new-nanobot` skill package and related helper scripts/templates, then switch `workspace/forms/deploy_new_agent/workflow.json` to the new stage skill.
5. Migrate tests, docs, and repo-local operator skills away from Nullclaw-specific paths and vocabulary.
6. Run validation: `uv run pytest -q` and `openspec validate --type change m07b-nanobot-runtime-migration --strict`.

Rollback:
- Before live reprovisioning, rollback is straightforward: restore the previous workflow skill binding, runtime command template, and schema/code changes.
- After agent folders and DB rows are migrated, rollback requires restoring prior DB metadata and recreating the old Nullclaw home-directory assets from backup; this should be treated as a manual recovery path, not an automatic downgrade.

## Open Questions

- Does the installed `nanobot` binary accept explicit config/workspace arguments for `gateway`, `agent`, and `status`, or is a wrapper/env-based invocation required?
- Should the new schema field be `runtime_config_path` (generic) or `nanobot_config_path` (runtime-specific)?
- Do current local AGENT nodes (`Director_01`, `HR_Head_01`, `Ops_Head_01`) need an automated migration helper, or is manual reprovisioning acceptable for the first Nanobot cutover?
