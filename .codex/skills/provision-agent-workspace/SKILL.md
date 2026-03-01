---
name: provision-agent-workspace
description: Combined end-to-end workflow to create Linux agent users, scaffold workspace structure, apply permissions, trigger kernel provisioning endpoints, and audit current agent permissions. Use for provisioning or validating agent workspaces.
license: MIT
compatibility: Linux host, Python 3.11+, optional sudoers integration
metadata:
  author: omniclaw
  version: "0.1"
---

Use this skill when you want one unified provisioning workflow.

## Installation

See [SETUP.md](./SETUP.md) for first-time setup, sudoers helper allowlist, and kernel env configuration.

## Scope

This skill combines previously split steps:
- Create/ensure Linux user
- Create/ensure OmniClaw workspace tree
- Apply owner + manager group permissions
- Trigger kernel endpoint action payloads
- Audit agents and permission state from SQLite + filesystem

## Scripts (bundled in this skill)

- `scripts/provision_agent_workflow.sh`: one entrypoint that chains local scripts.
- `scripts/create_linux_user.sh`: wrapper to repo provisioning script.
- `scripts/create_workspace_tree.py`: wrapper to repo provisioning script.
- `scripts/apply_workspace_permissions.sh`: wrapper to repo provisioning script.
- `scripts/trigger_kernel_action.sh`: wrapper to repo provisioning script.
- `scripts/list_agents_permissions.py`: prints agent + permission report.

## Quick Workflow

1. Dry-run local provisioning workflow:
   - `./scripts/provision_agent_workflow.sh --username agent_director_01 --workspace-root /home/agent_director_01/.nullclaw/workspace --manager-group sudo`
2. Apply local provisioning workflow:
   - `./scripts/provision_agent_workflow.sh --apply --username agent_director_01 --workspace-root /home/agent_director_01/.nullclaw/workspace --manager-group sudo`
3. Endpoint-triggered provisioning:
   - `./scripts/trigger_kernel_action.sh --apply --payload-file /home/macos/omniClaw/var/provisioning/create-agent-director-01.json`
4. Audit current agents and permissions:
   - `./scripts/list_agents_permissions.py --database /home/macos/omniClaw/omniclaw.db`

## Verification

- `id <username>`
- `getent passwd <username>`
- `ls -la /home/<username>/.nullclaw/config.json`
- `find <workspace-root> -maxdepth 2 -type d | sort`
- `./scripts/list_agents_permissions.py --database /home/macos/omniClaw/omniclaw.db`

## Related Docs

- [WORKFLOW.md](./WORKFLOW.md)
- [SETUP.md](./SETUP.md)
