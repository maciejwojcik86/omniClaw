---
name: deploy-new-claw-agent
description: End-to-end workflow to deploy a new Linux Nullclaw agent user with baseline ~/.nullclaw config, workspace scaffold, AGENTS.md instructions, permissions, kernel endpoint trigger, and permission audit.
license: MIT
compatibility: Linux host, Python 3.11+, optional sudoers helper integration
metadata:
  author: omniclaw
  version: "0.8"
---

Use this skill when you want to provision and bootstrap a new agent account that runs Nullclaw from `~/.nullclaw/workspace`.

## Installation

See [SETUP.md](./SETUP.md) for prerequisites and privileged helper setup.

## Scope

This skill covers the full deploy path:
- Create/ensure Linux user.
- Install/ensure one shared root-owned Nullclaw binary in `/opt/omniclaw`.
- Link per-user `~/.local/bin/nullclaw` to the shared binary.
- Create baseline provider-empty `~/.nullclaw/config.json` with heartbeat enabled (`agents.defaults.heartbeat.every=30m`).
- Create/ensure workspace tree at `~/.nullclaw/workspace`.
- Create workspace-root `HEARTBEAT.md` baseline checklist.
- Create workspace-root `AGENTS.md` system instructions.
- Apply owner + manager group permissions.
- Register existing kernel-running human user as a HUMAN node with repo-local workspace.
- Enforce line management contract: every AGENT has one manager node.
- Trigger kernel provisioning endpoint payloads.
- Audit current agent permissions from SQLite + filesystem.
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
- `scripts/grant_passwordless_sudo.sh`
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
   - `scripts/provisioning/install_shared_nullclaw_binary.sh --apply --binary-path /abs/path/to/nullclaw`
2. If direct sudo is restricted, export helper env once:
   - `export OMNICLAW_PROVISIONING_HELPER_PATH=/home/macos/omniClaw/scripts/provisioning/privileged_provisioning_helper.sh`
   - `export OMNICLAW_PROVISIONING_HELPER_USE_SUDO=true`
3. Dry-run deploy:
   - `scripts/provisioning/deploy_new_claw_agent.sh --username agent_hr_head_01 --node-name HR_Head_01 --manager-group sudo --shared-nullclaw-binary /opt/omniclaw/bin/nullclaw --manager-name Director_01 --role-name "Head of Human Resources" --agents-source-file /tmp/hr-head-01-AGENTS.md`
4. Apply deploy:
   - `scripts/provisioning/deploy_new_claw_agent.sh --apply --username agent_hr_head_01 --node-name HR_Head_01 --manager-group sudo --shared-nullclaw-binary /opt/omniclaw/bin/nullclaw --manager-name Director_01 --role-name "Head of Human Resources" --agents-source-file /tmp/hr-head-01-AGENTS.md`
5. Register/link in canonical DB via provisioning endpoint payload:
   - `scripts/provisioning/trigger_kernel_action.sh --apply --payload-file /tmp/create-agent-hr-head-01.json`
6. Optional manager superuser grant:
   - `scripts/provisioning/grant_passwordless_sudo.sh --apply --username agent_director_01`
7. Audit current nodes, managers, and permissions:
   - `uv run python scripts/provisioning/list_agents_permissions.py --database /home/macos/omniClaw/workspace/omniclaw.db`

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

## Related Docs

- [WORKFLOW.md](./WORKFLOW.md)
- [SETUP.md](./SETUP.md)
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- [AGENTS_AUTHORING.md](./AGENTS_AUTHORING.md)
