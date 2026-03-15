# Workflow: Deploy New Claw Agent

## Inputs

- `username` (required)
- `node_name` (required)
- `manager_group` (required)
- `manager_node_id` or `manager_node_name` (required for `provision_agent`)
- optional: `workspace_root` (default `/home/<user>/.nullclaw/workspace`)
- optional: `shared_nullclaw_binary` (default `/opt/omniclaw/bin/nullclaw`)
- optional: `bootstrap_shared_binary_from` (install/update shared binary before per-user link)
- optional: `manager_name`, `role_name`, `agents_source_file`, `shell`, `uid`

For existing kernel user HUMAN node:
- `username=macos` (or current kernel runner)
- `workspace_root=/home/<kernel-user>/omniClaw/workspace/<kernel-user>`

## Local execution path

1. `create_linux_user.sh` (dry-run then apply)
2. optional `install_shared_nullclaw_binary.sh` (one-time shared install to `/opt/omniclaw`)
3. `install_nullclaw_binary.sh` (create `~/.local/bin/nullclaw` symlink to shared binary)
4. `init_nullclaw_config.py` (write baseline `~/.nullclaw/config.json` with `agents.defaults.heartbeat.every=30m`)
5. `create_workspace_tree.py` (initial scaffold; helper fallback may create a minimal tree if home perms block non-root writes)
6. `apply_workspace_permissions.sh` (owner + manager-group permissions)
7. `create_workspace_tree.py` again (ensures missing baseline files such as `HEARTBEAT.md` after permissions are applied)
8. `write_agent_instructions.py` (write workspace-root `AGENTS.md`)
9. verify Linux user, shared binary link, Nullclaw config, heartbeat status, workspace, and AGENTS

All steps are orchestrated by `scripts/deploy_new_claw_agent.sh`.

### Non-root apply path (recommended when sudo is restricted)

Set once before running `--apply`:

```bash
export OMNICLAW_PROVISIONING_HELPER_PATH=/home/macos/omniClaw/scripts/provisioning/privileged_provisioning_helper.sh
export OMNICLAW_PROVISIONING_HELPER_USE_SUDO=true
```

With these env vars, deploy scripts call the allowlisted helper for privileged operations.

## Endpoint execution path

1. ensure kernel runs in `system` provisioning mode with helper allowlist
2. one-time app setup: register existing human supervisor node:
   - action: `register_human`
   - workspace inside repo root (`/home/<user>/omniClaw/workspace/<user>`)
3. bootstrap top agent with human manager:
   - action: `provision_agent`
   - include `manager_node_id` or `manager_node_name` for the human supervisor
4. for pre-existing agent rows or delegated teams, apply manager linkage:
   - action: `set_line_manager`
5. verify Linux user + Nullclaw files + workspace + DB node state

## Audit path

Use `list_agents_permissions.py` to print:
- HUMAN and AGENT node names
- current manager per node (if any)
- subordinate count
- status + autonomy
- uid and Linux username
- workspace owner/group/mode from `workspace_root`

## Line management rules

- AGENT nodes must have one and only one manager.
- Manager can be HUMAN or AGENT.
- HUMAN nodes have no required manager above them.
- One-time bootstrap baseline: HUMAN `macos` manages top AGENT `Director_01`.

## Failure handling

When errors occur, follow [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) as the canonical SOP.
