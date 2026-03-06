---
name: deploy-new-claw-agent
description: End-to-end workflow to deploy a new Linux Nullclaw agent user with baseline ~/.nullclaw config, workspace scaffold, AGENTS.md instructions, permissions, kernel endpoint trigger, and permission audit.
license: MIT
compatibility: Linux host, Python 3.11+, optional sudoers helper integration
metadata:
  author: omniclaw
  version: "0.9"
---

Stage: `AGENT_DEPLOYMENT`
Allowed decision:
- `deploy_and_archive`

Use this skill when you want to provision and bootstrap a new agent account that runs Nullclaw from `~/.nullclaw/workspace`.

## Installation

See [SETUP.md](./SETUP.md) for prerequisites and privileged helper setup.

## Scope

This skill covers the full deploy path:
- Create/ensure Linux user.
- Install/ensure one shared root-owned Nullclaw binary in `/opt/omniclaw`.
- Link per-user `~/.local/bin/nullclaw` to the shared binary.
- Initialize baseline `~/.nullclaw/config.json` and then seed runtime config from
  `templates/director_seed_config.json` for this stage workflow.
- Create/ensure workspace tree at `~/.nullclaw/workspace`.
- Create workspace-root `HEARTBEAT.md` baseline checklist.
- Create workspace-root `AGENTS.md` system instructions.
- Apply owner + manager group permissions.
- Register existing kernel-running human user as a HUMAN node with repo-local workspace.
- Enforce line management contract: every AGENT has one manager node.
- Trigger kernel provisioning endpoint payloads.
- Audit current agent permissions from SQLite + filesystem.
- Seed runtime config from `templates/director_seed_config.json` for workflow consistency.
- Sync `auth.json` from director account when live model access is needed in smoke runs.
- Set autonomy level to `full` for `Director_01`, `HR_Head_01`, and `Ops_Head_01` before live-agent smoke.
- Support non-root `--apply` execution via allowlisted privileged helper (`OMNICLAW_PROVISIONING_HELPER_PATH`) when direct sudo is restricted.
- Optionally grant passwordless sudo for designated manager-level agents.

## AGENTS.md Writing Guidance

Use [AGENTS_AUTHORING.md](./AGENTS_AUTHORING.md) to write clear, durable agent system instructions.

## Scripts (bundled in this skill)

Primary entrypoint:
- `scripts/deploy_new_claw_agent.sh`: unified local deploy flow.

Core helper wrappers:
- `scripts/create_linux_user.sh`
- `scripts/install_shared_nullclaw_binary.sh`
- `scripts/install_nullclaw_binary.sh`
- `scripts/sync_nullclaw_auth.sh`
- `scripts/init_nullclaw_config.py`
- `scripts/create_workspace_tree.py`
- `scripts/write_agent_instructions.py`
- `scripts/apply_workspace_permissions.sh`

Endpoint + audit wrappers:
- `scripts/trigger_kernel_action.sh`
- `scripts/list_agents_permissions.py`

Legacy compatibility:
- `scripts/provision_agent_workflow.sh` (older workflow wrapper)

## Quick Workflow

1. Ensure shared binary exists:
   - `scripts/install_shared_nullclaw_binary.sh --apply --binary-path /abs/path/to/nullclaw`
2. If direct sudo is restricted, export helper env once:
   - `export OMNICLAW_PROVISIONING_HELPER_PATH=/home/macos/omniClaw/scripts/provisioning/privileged_provisioning_helper.sh`
   - `export OMNICLAW_PROVISIONING_HELPER_USE_SUDO=true`
3. Dry-run deploy:
   - `scripts/deploy_new_claw_agent.sh --username agent_hr_head_01 --node-name HR_Head_01 --manager-group sudo --shared-nullclaw-binary /opt/omniclaw/bin/nullclaw --manager-name Director_01 --role-name "Head of Human Resources" --agents-source-file /tmp/hr-head-01-AGENTS.md`
4. Apply deploy:
   - `scripts/deploy_new_claw_agent.sh --apply --username agent_hr_head_01 --node-name HR_Head_01 --manager-group sudo --shared-nullclaw-binary /opt/omniclaw/bin/nullclaw --manager-name Director_01 --role-name "Head of Human Resources" --agents-source-file /tmp/hr-head-01-AGENTS.md`
5. Seed runtime config from stage template (`templates/director_seed_config.json`, copied from director baseline during M07):
   - `install -m 600 templates/director_seed_config.json /home/<new_user>/.nullclaw/config.json`
6. Sync director auth token to new account (live smoke path only):
   - `scripts/sync_nullclaw_auth.sh --apply --source-user agent_director_01 --target-user <new_user>`
7. Register/link in canonical DB via provisioning endpoint payload:
   - `scripts/trigger_kernel_action.sh --apply --payload-file /tmp/create-agent-hr-head-01.json`
8. Live smoke preflight: set autonomy `full` for current workflow actors:
   - `python3 -c 'import json, pathlib; p=pathlib.Path(\"/home/agent_director_01/.nullclaw/config.json\"); d=json.loads(p.read_text()); d.setdefault(\"autonomy\", {})[\"level\"]=\"full\"; p.write_text(json.dumps(d, indent=2)+\"\\n\")'`
   - Repeat for `/home/agent_hr_head_01/.nullclaw/config.json` and `/home/agent_ops_head_01/.nullclaw/config.json`.
9. Audit current nodes, managers, and permissions:
   - `uv run python scripts/provisioning/list_agents_permissions.py --database /home/macos/omniClaw/workspace/omniclaw.db`

## Live Smoke Preparation (Operator-Driven)

Use this before running `scripts/forms/smoke_deploy_new_agent_e2e.sh --apply`:

1. Confirm actor readiness:
   - `Director_01`, `HR_Head_01`, and `Ops_Head_01` each have workspace-root `AGENTS.md` and `HEARTBEAT.md`.
2. Seed config from this skill package template when missing/inconsistent:
   - `install -m 600 templates/director_seed_config.json /home/<actor_linux_user>/.nullclaw/config.json`
3. Sync auth from director into HR/Ops (live model access):
   - `scripts/sync_nullclaw_auth.sh --apply --source-user agent_director_01 --target-user agent_hr_head_01`
   - `scripts/sync_nullclaw_auth.sh --apply --source-user agent_director_01 --target-user agent_ops_head_01`
4. Set autonomy to `full` for director/hr/ops configs before smoke.
5. Validate each routed hop includes kernel-managed `stage_skill`.

Notes:
- Config/auth/autonomy propagation stays operator-driven in M07.
- Kernel routing does not auto-provision users at approval transitions.
- `templates/director_seed_config.json` is a sanitized seed; set environment-specific secrets before use.

## Line Management Contract

- Every AGENT must be linked to exactly one manager.
- Manager can be HUMAN or AGENT (supports delegated hierarchy).
- HUMAN nodes do not require a manager above them.
- App bootstrap should create one HUMAN supervisor (`macos`) that manages the top agent (`Director_01`).
- Use provisioning payloads with `manager_node_id` or `manager_node_name` to enforce manager linkage at provisioning time.
- Use `set_line_manager` provisioning action to link existing AGENT nodes.

## Verification

- `id <username>`
- `ls -la /opt/omniclaw/bin/nullclaw`
- `ls -la /home/<username>/.local/bin/nullclaw` (should be symlink to `/opt/omniclaw/bin/nullclaw`)
- `ls -la /home/<username>/.nullclaw/config.json`
- `HOME=/home/<username> /opt/omniclaw/bin/nullclaw status | rg -n "Heartbeat"`
- `find /home/<username>/.nullclaw/workspace -maxdepth 2 -type d | sort`
- `ls -la /home/<username>/.nullclaw/workspace/HEARTBEAT.md`
- `ls -la /home/<username>/.nullclaw/workspace/AGENTS.md`
- `uv run python scripts/provisioning/list_agents_permissions.py --database /home/macos/omniClaw/workspace/omniclaw.db`

## Troubleshooting SOP

If deployment or first run fails (for example `uv: command not found`, shared binary resolution errors, or `AllProvidersFailed`), use:
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

## Archiving

After succesful deployment of new agent, archive this form by appending execution report:
- Use `templates/deployment_execution.md`.
- Append the execution log section to the existing form.
- If deployment succeeded, set `decision: deploy_and_archive`.
- Save updated form to `/outbox/pending/`.

## Related Docs

- [WORKFLOW.md](./WORKFLOW.md)
- [SETUP.md](./SETUP.md)
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- [AGENTS_AUTHORING.md](./AGENTS_AUTHORING.md)
