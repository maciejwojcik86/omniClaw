---
name: deploy-new-nanobot
description: End-to-end workflow to deploy a repo-local Nanobot agent with a sibling config.json, OmniClaw workspace scaffold, kernel provisioning payload, and optional packaged runtime source artifact.
license: MIT
compatibility: Linux/macOS host, Python 3.11+, Nanobot CLI available or packaged from local fork
metadata:
  author: omniclaw
  version: "1.0"
---

Stage: `AGENT_DEPLOYMENT`
Allowed decision:
- `deploy_and_archive`

Use this skill when you want to provision and bootstrap a Nanobot agent under `workspace/agents/<agent_name>/`.

## Installation

See [SETUP.md](./SETUP.md) for Nanobot install and packaging options.

## Scope

This skill covers the canonical Nanobot deploy path:
- Scaffold the repo-local agent workspace at `workspace/agents/<agent_name>/workspace/`.
- Write or update the sibling Nanobot runtime config at `workspace/agents/<agent_name>/config.json` using the canonical template at `/home/macos/omniClaw/workspace/nanobot_workspace_templates/config.json`.
- Write workspace-root `AGENTS.md` instructions and preserve the Nanobot-native context files using the canonical files under `/home/macos/omniClaw/workspace/nanobot_workspace_templates/`.
- Register or update the AGENT node through the kernel `provision_agent` action.
- Keep line-management semantics intact: every AGENT still has one manager node.
- Optionally package the vendored monorepo `third_party/nanobot/` fork into a reusable source archive for another machine.
- Provide explicit `nanobot gateway -w -c` and `nanobot agent -w -c` smoke commands.

## Layout Contract

Each deployed agent uses this layout:

```text
workspace/agents/<agent_name>/
├── config.json
└── workspace/
    ├── AGENTS.md
    ├── HEARTBEAT.md
    ├── SOUL.md
    ├── TOOLS.md
    ├── USER.md
    ├── inbox/
    ├── outbox/
    ├── memory/
    ├── sessions/
    └── skills/
```

Notes:
- `workspace_root` in the DB remains the nested `workspace/` directory.
- Skills are copied into `workspace/.../skills/` as markdown/script folders; no `skill.json` metadata is required inside Nanobot workspaces.
- `config.json` stays next to the workspace, not inside it.

## AGENTS.md Writing Guidance

Use [AGENTS_AUTHORING.md](./AGENTS_AUTHORING.md) to write clear, durable Nanobot-facing instructions.

## Scripts (bundled in this skill)

Primary entrypoint:
- `skills/deploy-new-nanobot/scripts/deploy_new_nanobot.sh`: unified local deploy flow for the Nanobot layout.

Core helper wrappers:
- `skills/deploy-new-nanobot/scripts/package_nanobot_source.sh`
- `skills/deploy-new-nanobot/scripts/create_workspace_tree.py`
- `skills/deploy-new-nanobot/scripts/init_nanobot_config.py`
- `skills/deploy-new-nanobot/scripts/write_agent_instructions.py`

Endpoint + audit wrappers:
- `skills/deploy-new-nanobot/scripts/trigger_kernel_action.sh`
- `skills/deploy-new-nanobot/scripts/list_agents_permissions.py`

Compatibility wrappers:
- `skills/deploy-new-nanobot/scripts/deploy_new_nanobot_agent.sh`
- `skills/deploy-new-nanobot/scripts/provision_agent_workflow.sh`

## Quick Workflow

1. Optional: package the local Nanobot fork so another machine can install the same runtime:
   - `skills/deploy-new-nanobot/scripts/package_nanobot_source.sh --apply --source-dir /home/macos/omniClaw/third_party/nanobot --output-dir /home/macos/.omniClaw/workspace/runtime_packages`
2. Dry-run deployment:
   - `skills/deploy-new-nanobot/scripts/deploy_new_nanobot.sh --username agent_hr_head_01 --node-name HR_Head_01 --manager-name Director_01 --role-name "Head of Human Resources" --agents-source-file /tmp/hr-head-01-AGENTS.md --seed-config skills/deploy-new-nanobot/templates/nanobot_seed_config.json`
3. Apply deployment:
   - `skills/deploy-new-nanobot/scripts/deploy_new_nanobot.sh --apply --username agent_hr_head_01 --node-name HR_Head_01 --manager-name Director_01 --role-name "Head of Human Resources" --agents-source-file /tmp/hr-head-01-AGENTS.md --seed-config skills/deploy-new-nanobot/templates/nanobot_seed_config.json`
4. Manual runtime smoke:
   - `nanobot gateway -w /home/macos/omniClaw/workspace/agents/HR_Head_01/workspace -c /home/macos/omniClaw/workspace/agents/HR_Head_01/config.json -p 18792`
   - `nanobot agent -w /home/macos/omniClaw/workspace/agents/HR_Head_01/workspace -c /home/macos/omniClaw/workspace/agents/HR_Head_01/config.json -m "hello"`
5. Audit canonical node state:
   - `python3 skills/deploy-new-nanobot/scripts/list_agents_permissions.py --database /home/macos/omniClaw/workspace/omniclaw.db`

## Default Skill Assignment

- New agents receive company-configured default loose skills during provisioning.
- Current default set:
  - `form_workflow_authoring`
- Review active loose skills available for post-deploy assignment:
  - `bash /home/macos/omniClaw/scripts/skills/list_active_master_skills.sh --apply`
- Inspect the deployed agent's current effective skill set:
  - `bash /home/macos/omniClaw/scripts/skills/list_agent_skill_assignments.sh --apply --target-node-name <agent_name>`
- Add multiple loose skills after deployment in one request:
  - `bash /home/macos/omniClaw/scripts/skills/assign_agent_skills.sh --apply --target-node-name <agent_name> --skill-names "skill_a,skill_b"`
- Remove multiple manually assigned loose skills:
  - `bash /home/macos/omniClaw/scripts/skills/remove_agent_skills.sh --apply --target-node-name <agent_name> --skill-names "skill_a,skill_b"`

## Live Smoke Preparation

Use this before running `scripts/forms/smoke_deploy_new_agent_e2e.sh --apply`:

1. Confirm `Director_01`, `HR_Head_01`, and `Ops_Head_01` each have repo-local workspaces and sibling Nanobot config files.
2. Re-run `scripts/init_nanobot_config.py --apply` for any actor whose config drifted from the approved baseline.
   The baseline template lives at `/home/macos/omniClaw/workspace/nanobot_workspace_templates/config.json`.
3. Verify the tested direct commands work for each actor:
   - `nanobot gateway -w <workspace_root> -c <config_path> -p <port>`
   - `nanobot agent -w <workspace_root> -c <config_path> -m "heartbeat smoke"`
4. Validate each routed hop still includes kernel-managed `stage_skill`.
5. If the target host needs your local Nanobot fork, archive it first and install from that archive on the destination host.

## Line Management Contract

- Every AGENT must be linked to exactly one manager.
- Manager can be HUMAN or AGENT.
- HUMAN nodes do not require a manager above them.
- Use `manager_node_id` or `manager_node_name` when calling `provision_agent`.
- Use `set_line_manager` only for pre-existing AGENT rows that need manager linkage after the fact.

## Verification

- `ls -la /home/macos/omniClaw/workspace/agents/<agent_name>/config.json`
- `find /home/macos/omniClaw/workspace/agents/<agent_name>/workspace -maxdepth 2 -type d | sort`
- `ls -la /home/macos/omniClaw/workspace/agents/<agent_name>/workspace/AGENTS.md`
- `ls -la /home/macos/omniClaw/workspace/agents/<agent_name>/workspace/HEARTBEAT.md`
- `nanobot gateway -w /home/macos/omniClaw/workspace/agents/<agent_name>/workspace -c /home/macos/omniClaw/workspace/agents/<agent_name>/config.json -p 18790`
- `nanobot agent -w /home/macos/omniClaw/workspace/agents/<agent_name>/workspace -c /home/macos/omniClaw/workspace/agents/<agent_name>/config.json -m "hello"`
- `python3 skills/deploy-new-nanobot/scripts/list_agents_permissions.py --database /home/macos/omniClaw/workspace/omniclaw.db`

## Troubleshooting SOP

If deployment or first runtime smoke fails, use [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

## Failure Handling

If deployment is blocked or fails:
- Append a full execution report with the failure details and next-step owner.
- Keep `decision` empty.
- Leave the form in `inbox/new/` for retry or human remediation; do not move it to `/outbox/send/`.
- Only set `decision: deploy_and_archive` after the provisioning path and smoke checks succeed.

## Archiving

After successful deployment of a new agent, archive this form by appending the execution report:
- Use `templates/deployment_execution.md`.
- Record the final workspace path, config path, packaged runtime artifact path, and smoke command results.
- If deployment succeeded, set `decision: deploy_and_archive`.
- Save the updated form to `/outbox/send/`.

## Related Docs

- [WORKFLOW.md](./WORKFLOW.md)
- [SETUP.md](./SETUP.md)
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- [AGENTS_AUTHORING.md](./AGENTS_AUTHORING.md)
