# Setup: Runtime Gateway Control

## Prerequisites

- OmniClaw service running (`uv run python main.py`).
- Database migrated to head (`uv run alembic upgrade head`).
- Runtime config enabled.

## Runtime Environment (system mode)

Set these for real host control:

```bash
export OMNICLAW_RUNTIME_MODE=system
export OMNICLAW_ALLOW_PRIVILEGED_RUNTIME=true
export OMNICLAW_RUNTIME_USE_SUDO=true
export OMNICLAW_RUNTIME_GATEWAY_COMMAND_TEMPLATE='nanobot gateway --workspace {workspace_root} --config {config_path} --port {port}'
export OMNICLAW_RUNTIME_COMMAND_TIMEOUT_SECONDS=30
export OMNICLAW_RUNTIME_OUTPUT_BOUNDARY_REL='drafts/runtime'
```

For local tests only, use mock mode:

```bash
export OMNICLAW_RUNTIME_MODE=mock
```

## Notes

- `gateway_*` actions require `node_id` or `node_name` of an AGENT row.
- Runtime writes metadata under each agent workspace output boundary.
