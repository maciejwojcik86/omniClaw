# Workflow: Runtime Gateway On/Off Control

## Operator Sequence

1. Confirm agent exists in DB:
- `./scripts/provisioning/list_agents_permissions.py --database /home/macos/omniClaw/workspace/omniclaw.db`

2. Start gateway:
- `./scripts/trigger_runtime_action.sh --apply --action gateway_start --node-name Director_01 --gateway-host 127.0.0.1 --gateway-port 3000`

3. Check status:
- `./scripts/trigger_runtime_action.sh --apply --action gateway_status --node-name Director_01`

4. Stop gateway:
- `./scripts/trigger_runtime_action.sh --apply --action gateway_stop --node-name Director_01`

5. Re-check status:
- `./scripts/trigger_runtime_action.sh --apply --action gateway_status --node-name Director_01`

6. List all tracked agents:
- `./scripts/trigger_runtime_action.sh --apply --action list_agents`

## Smoke Shortcut

- `./scripts/smoke_gateway_control.sh --apply --node-name Director_01`

## Expected Results

- Start response shows `gateway.running=true`.
- Stop response shows `gateway.running=false`.
- Node payload includes updated `gateway_started_at` / `gateway_stopped_at`.
- Metadata JSON exists under `<workspace>/drafts/runtime/runs`.
