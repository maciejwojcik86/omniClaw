# Workflow: Deploy New Nanobot

## Inputs

- `username` (required)
- `node_name` (required)
- `manager_node_id` or `manager_node_name` (required for `provision_agent`)
- optional: `workspace_root` (default `workspace/agents/<node_name>/workspace`)
- optional: `config_path` (default sibling `workspace/agents/<node_name>/config.json`)
- optional: `seed_config` (`skills/deploy-new-nanobot/templates/nanobot_seed_config.json`)
- optional: `primary_model`, `gateway_port`, `gateway_host`
- optional: `nanobot_source` and `package_output_dir` when you want a reusable archive of the local Nanobot fork
- optional: `manager_name`, `role_name`, `agents_source_file`, `shell`, `uid`

For existing kernel user HUMAN node:
- `username=macos` (or current kernel runner)
- `workspace_root=/home/<kernel-user>/omniClaw/workspace/<kernel-user>`

## Local execution path

1. optional `skills/deploy-new-nanobot/scripts/package_nanobot_source.sh` (archive the vendored `third_party/nanobot` fork)
2. `skills/deploy-new-nanobot/scripts/trigger_kernel_action.sh` with action `provision_agent`
3. `skills/deploy-new-nanobot/scripts/create_workspace_tree.py` (write the OmniClaw/Nanobot workspace scaffold from `/home/macos/omniClaw/workspace/nanobot_workspace_templates/`)
4. `skills/deploy-new-nanobot/scripts/init_nanobot_config.py` (write or update the sibling `config.json` from `/home/macos/omniClaw/workspace/nanobot_workspace_templates/config.json`)
5. `skills/deploy-new-nanobot/scripts/write_agent_instructions.py` (write workspace-root `AGENTS.md` from `/home/macos/omniClaw/workspace/nanobot_workspace_templates/AGENTS.md`)
6. verify workspace tree, config path, DB node linkage, and manual `nanobot gateway/agent -w -c` smoke commands

All steps are orchestrated by `skills/deploy-new-nanobot/scripts/deploy_new_nanobot.sh`.

## Endpoint execution path

1. ensure the kernel is running
2. one-time app setup: register existing human supervisor node:
   - action: `register_human`
   - workspace inside repo root (`/home/<user>/omniClaw/workspace/<user>`)
3. bootstrap top agent with human manager:
   - action: `provision_agent`
   - include repo-local `workspace_root`
   - include sibling `runtime_config_path`
   - include `manager_node_id` or `manager_node_name` for the human supervisor
4. for pre-existing agent rows or delegated teams, apply manager linkage:
   - action: `set_line_manager`
5. verify Nanobot config + workspace + DB node state

## Audit path

Use `list_agents_permissions.py` to print:
- HUMAN and AGENT node names
- current manager per node (if any)
- subordinate count
- status + autonomy
- uid and Linux username
- runtime config path
- workspace owner/group/mode from `workspace_root`

## Line management rules

- AGENT nodes must have one and only one manager.
- Manager can be HUMAN or AGENT.
- HUMAN nodes have no required manager above them.
- One-time bootstrap baseline: HUMAN `macos` manages top AGENT `Director_01`.

## Failure handling

When errors occur:
- follow [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) as the canonical SOP
- append the failed execution report to the form
- keep `decision` empty
- leave the form in `inbox/new/` until the blocker is fixed

Only route the form to `outbox/send/` when deployment and smoke verification have succeeded and you can truthfully set `decision: deploy_and_archive`.
