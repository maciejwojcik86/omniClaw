# Workflow: Provision Agent Workspace

## Inputs

- `username` (required)
- `workspace_root` (required)
- `manager_group` (required)
- optional: `shell`, `uid`, endpoint payload path

## Local execution path

1. `create_linux_user.sh` (dry-run then apply)
2. `create_workspace_tree.py` (dry-run then apply)
3. `apply_workspace_permissions.sh` (dry-run then apply)
4. verify user + workspace

## Endpoint execution path

1. ensure kernel is running with system provisioning mode
2. submit JSON payload through `trigger_kernel_action.sh`
3. verify user + workspace + DB node status

## Audit path

Use `list_agents_permissions.py` to print:
- AGENT node name
- status + autonomy
- uid and Linux username
- `/home/<user>` owner/group/mode
- `/home/<user>/workspace` owner/group/mode
