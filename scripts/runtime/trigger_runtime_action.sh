#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  trigger_runtime_action.sh [--apply] [--kernel-url <url>] [--endpoint <path>] --action <action>
                            [--node-id <id>] [--node-name <name>] [--task-key <key>]
                            [--gateway-host <host>] [--gateway-port <port>] [--force-restart <true|false>]
                            [--prompt <text>] [--session-key <key>] [--markdown <true|false>] [--include-logs <true|false>]

Default mode is dry-run. Use --apply to execute HTTP POST.
Actions: gateway_start, gateway_stop, gateway_status, list_agents, invoke_prompt, process_due_retries, retry_now, cancel_retry
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
prompt=""
session_key="cli:verification"
markdown="false"
include_logs="false"
task_key=""

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
    --prompt)
      prompt="$2"
      shift 2
      ;;
    --session-key)
      session_key="$2"
      shift 2
      ;;
    --markdown)
      markdown="$2"
      shift 2
      ;;
    --include-logs)
      include_logs="$2"
      shift 2
      ;;
    --task-key)
      task_key="$2"
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
  gateway_start|gateway_stop|gateway_status|list_agents|invoke_prompt|process_due_retries|retry_now|cancel_retry)
    ;;
  *)
    echo "Invalid --action '$action'" >&2
    usage
    exit 1
    ;;
esac

if [[ "$action" != "list_agents" && "$action" != "process_due_retries" && "$action" != "retry_now" && "$action" != "cancel_retry" && -z "$node_id" && -z "$node_name" ]]; then
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

case "$markdown" in
  true|false)
    ;;
  *)
    echo "--markdown must be true or false" >&2
    exit 1
    ;;
esac

case "$include_logs" in
  true|false)
    ;;
  *)
    echo "--include-logs must be true or false" >&2
    exit 1
    ;;
esac

if [[ "$action" == "invoke_prompt" && -z "$prompt" ]]; then
  echo "--prompt is required for action 'invoke_prompt'" >&2
  exit 1
fi

if [[ "$action" == "retry_now" || "$action" == "cancel_retry" ]]; then
  if [[ -z "$task_key" ]]; then
    echo "--task-key is required for action '$action'" >&2
    exit 1
  fi
fi

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
  "force_restart": $force_restart,
  "prompt": $(python3 -c 'import json,sys; print(json.dumps(sys.argv[1] if sys.argv[1] else None))' "$prompt"),
  "session_key": $(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$session_key"),
  "markdown": $markdown,
  "include_logs": $include_logs,
  "task_key": $(python3 -c 'import json,sys; print(json.dumps(sys.argv[1] if sys.argv[1] else None))' "$task_key")
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
