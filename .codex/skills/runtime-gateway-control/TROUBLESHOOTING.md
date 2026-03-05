# Troubleshooting: Runtime Gateway Control

## 403 "System runtime control is disabled"

Cause:
- `OMNICLAW_ALLOW_PRIVILEGED_RUNTIME` is not enabled in system mode.

Fix:
- Set `OMNICLAW_ALLOW_PRIVILEGED_RUNTIME=true` and restart kernel service.

## 500 "runtime_use_sudo=false but target user differs"

Cause:
- Kernel user is not the target Linux user and sudo switching is disabled.

Fix:
- Set `OMNICLAW_RUNTIME_USE_SUDO=true` for cross-user control.

## 404 "agent node not found"

Cause:
- Wrong `node_name`/`node_id`, or node type is not AGENT.

Fix:
- Use `list_agents_permissions.py` to confirm the exact agent name/id.

## 500 gateway start/stop failure with exit code

Cause:
- Nullclaw binary or auth/config is missing for target user, or permissions block command execution.

Fix:
- Re-run `$deploy-new-claw-agent` workflow for that user.
- Verify shared binary link: `/home/<user>/.local/bin/nullclaw`.
- Verify config/auth under `/home/<user>/.nullclaw/`.

## `already_running` / `already_stopped`

Cause:
- Idempotent lifecycle call state.

Fix:
- This is expected; use `gateway_status` to reconcile runtime state.
