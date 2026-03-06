#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  trigger_runtime_action.sh [--apply] [--kernel-url <url>] [--endpoint <path>] --action <action>
                            [--node-id <id>] [--node-name <name>]
                            [--gateway-host <host>] [--gateway-port <port>] [--force-restart <true|false>]

Default mode is dry-run. Use --apply to execute HTTP POST.
Actions: gateway_start, gateway_stop, gateway_status, list_agents
USAGE
}

dry_run=1
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
endpoint="/v1/runtime/actions"
action=""
node_id=""
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
    --endpoint)
      endpoint="$2"
      shift 2
      ;;
    --action)
      action="$2"
      shift 2
      ;;
    --node-id)
      node_id="$2"
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
      force_restart="$2"
      shift 2
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

if [[ -z "$action" ]]; then
  echo "--action is required" >&2
  usage
  exit 1
fi

case "$action" in
  gateway_start|gateway_stop|gateway_status|list_agents)
    ;;
  *)
    echo "Invalid --action '$action'" >&2
    usage
    exit 1
    ;;
esac

if [[ "$action" != "list_agents" && -z "$node_id" && -z "$node_name" ]]; then
  echo "--node-id or --node-name is required for action '$action'" >&2
  exit 1
fi

if ! [[ "$gateway_port" =~ ^[0-9]+$ ]]; then
  echo "--gateway-port must be an integer" >&2
  exit 1
fi

case "$force_restart" in
  true|false)
    ;;
  *)
    echo "--force-restart must be true or false" >&2
    exit 1
    ;;
esac

node_id_json="null"
node_name_json="null"
if [[ -n "$node_id" ]]; then
  node_id_json="\"$node_id\""
fi
if [[ -n "$node_name" ]]; then
  node_name_json="\"$node_name\""
fi

payload_file="$(mktemp)"
trap 'rm -f "$payload_file"' EXIT

cat > "$payload_file" <<JSON
{
  "action": "$action",
  "node_id": $node_id_json,
  "node_name": $node_name_json,
  "gateway_host": "$gateway_host",
  "gateway_port": $gateway_port,
  "force_restart": $force_restart
}
JSON

url="${kernel_url%/}${endpoint}"

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN runtime request: POST $url"
  cat "$payload_file"
  exit 0
fi

curl --fail --show-error --silent \
  -X POST \
  -H 'Content-Type: application/json' \
  --data-binary "@$payload_file" \
  "$url"

echo
