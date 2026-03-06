---
name: runtime-gateway-control
description: Control deployed agent Nanobot gateways via kernel runtime endpoints (start, stop, status, list) and verify DB running-state tracking. Use when operators or delegated automation need to enable/disable agent runtime.
license: MIT
compatibility: Linux host, Python 3.11+, running OmniClaw kernel API
metadata:
  author: omniclaw
  version: "0.1"
---

Use this skill when you need to turn agent gateways on/off and keep canonical runtime state synchronized in the kernel database.

## Installation

See [SETUP.md](./SETUP.md) for runtime endpoint prerequisites.

## Scope

This skill covers:
- Calling `POST /v1/runtime/actions` for `gateway_start`, `gateway_stop`, `gateway_status`, and `list_agents`.
- Running a deterministic smoke sequence for one agent.
- Verifying runtime state in API responses and SQLite (`nodes.gateway_*` fields).

## Inputs

Required:
- `node_name` or `node_id` for gateway actions.

Optional:
- `kernel_url` (default `http://127.0.0.1:8000`)
- `gateway_host` (default `127.0.0.1`)
- `gateway_port` (default `18790`)
- `force_restart` for `gateway_start`

Host validation:
- `gateway_host` must be a valid IP address or hostname.
- Invalid host input is rejected with HTTP `422` and gateway is not started.

## Scripts (bundled in this skill)

- `scripts/trigger_runtime_action.sh`: single runtime action caller.
- `scripts/smoke_gateway_control.sh`: end-to-end sequence (`start -> status -> stop -> status -> list`).

## Quick Workflow

1. Dry-run one action:
   - `./scripts/trigger_runtime_action.sh --action gateway_status --node-name Director_01`
2. Dry-run smoke sequence:
   - `./scripts/smoke_gateway_control.sh --node-name Director_01`
3. Apply smoke sequence:
   - `./scripts/smoke_gateway_control.sh --apply --node-name Director_01 --gateway-port 18790`
4. Verify DB/runtime state:
   - `./scripts/provisioning/list_agents_permissions.py --database /home/macos/omniClaw/workspace/omniclaw.db`

## Verification

- Runtime endpoint returns `mode`, `gateway.status`, and serialized `node.gateway_*` values.
- `gateway_start` updates `gateway_running=true` and `gateway_started_at`.
- `gateway_stop` updates `gateway_running=false` and `gateway_stopped_at`.
- Metadata JSON files are written under `<workspace>/drafts/runtime/runs`.

## Fallback

If `gateway_start` returns validation error:
1. Correct `gateway_host` to valid IP/hostname (for example `127.0.0.1`).
2. Re-run `gateway_start`.
3. Verify with `gateway_status`.

## Related Docs

- [WORKFLOW.md](./WORKFLOW.md)
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- `openspec/changes/m04-agent-runtime-bootstrap/`
