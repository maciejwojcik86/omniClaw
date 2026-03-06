#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  smoke_gateway_control.sh [--apply] [--kernel-url <url>] --node-name <name>
                           [--gateway-host <host>] [--gateway-port <port>] [--force-restart]

Default mode is dry-run. Use --apply to execute HTTP POST requests.
This script runs: gateway_start -> gateway_status -> gateway_stop -> gateway_status -> list_agents.
USAGE
}

dry_run=1
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
node_name=""
gateway_host="127.0.0.1"
gateway_port="18790"
force_restart="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      dry_run=0
      shift
      ;;
    --kernel-url)
      kernel_url="$2"
      shift 2
      ;;
    --node-name)
      node_name="$2"
      shift 2
      ;;
    --gateway-host)
      gateway_host="$2"
      shift 2
      ;;
    --gateway-port)
      gateway_port="$2"
      shift 2
      ;;
    --force-restart)
      force_restart="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$node_name" ]]; then
  echo "--node-name is required" >&2
  usage
  exit 1
fi

apply_flag=()
if [[ "$dry_run" -eq 0 ]]; then
  apply_flag=(--apply)
fi

echo "[1/5] gateway_start for node '$node_name'"
"$ROOT/scripts/runtime/trigger_runtime_action.sh" \
  "${apply_flag[@]}" \
  --kernel-url "$kernel_url" \
  --action gateway_start \
  --node-name "$node_name" \
  --gateway-host "$gateway_host" \
  --gateway-port "$gateway_port" \
  --force-restart "$force_restart"

echo "[2/5] gateway_status for node '$node_name'"
"$ROOT/scripts/runtime/trigger_runtime_action.sh" \
  "${apply_flag[@]}" \
  --kernel-url "$kernel_url" \
  --action gateway_status \
  --node-name "$node_name"

echo "[3/5] gateway_stop for node '$node_name'"
"$ROOT/scripts/runtime/trigger_runtime_action.sh" \
  "${apply_flag[@]}" \
  --kernel-url "$kernel_url" \
  --action gateway_stop \
  --node-name "$node_name"

echo "[4/5] gateway_status for node '$node_name'"
"$ROOT/scripts/runtime/trigger_runtime_action.sh" \
  "${apply_flag[@]}" \
  --kernel-url "$kernel_url" \
  --action gateway_status \
  --node-name "$node_name"

echo "[5/5] list_agents"
"$ROOT/scripts/runtime/trigger_runtime_action.sh" \
  "${apply_flag[@]}" \
  --kernel-url "$kernel_url" \
  --action list_agents

echo "Smoke sequence finished."
