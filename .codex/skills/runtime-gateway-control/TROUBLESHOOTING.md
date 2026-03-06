# Troubleshooting: Runtime Gateway Control

## 403 "System runtime control is disabled"

Cause:
- `OMNICLAW_ALLOW_PRIVILEGED_RUNTIME` is not enabled in system mode.

Fix:
- Set `OMNICLAW_ALLOW_PRIVILEGED_RUNTIME=true` and restart kernel service.

## 409/500 runtime launch path mismatch

Cause:
- Runtime metadata is missing, the workspace/config path is wrong, or the configured launch template does not match the Nanobot contract.

Fix:
- Verify `workspace_root` and `runtime_config_path` on the AGENT row.
- Verify the runtime template uses explicit Nanobot inputs:
  - `nanobot gateway --workspace {workspace_root} --config {config_path} --port {port}`

## 404 "agent node not found"

Cause:
- Wrong `node_name`/`node_id`, or node type is not AGENT.

Fix:
- Use `list_agents_permissions.py` to confirm the exact agent name/id.

## 500 gateway start/stop failure with exit code

Cause:
- Nanobot binary is missing, the agent config/workspace path is wrong, or the runtime command fails inside the configured workspace boundary.

Fix:
- Re-run `$deploy-new-nanobot` for that agent.
- Verify config path: `workspace/agents/<agent_name>/config.json`.
- Verify workspace root: `workspace/agents/<agent_name>/workspace/`.
- Run a manual smoke command:
  - `nanobot agent -w <workspace_root> -c <config_path> -m "hello"`

## `already_running` / `already_stopped`

Cause:
- Idempotent lifecycle call state.

Fix:
- This is expected; use `gateway_status` to reconcile runtime state.
