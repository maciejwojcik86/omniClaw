#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  invoke_agent_prompt.sh [--apply] [--kernel-url <url>] [--endpoint <path>]
                         (--node-id <id> | --node-name <name>)
                         --prompt <text>
                         [--session-key <key>] [--markdown] [--include-logs]

Default mode is dry-run. Use --apply to execute HTTP POST.
USAGE
}

dry_run=1
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
endpoint="/v1/runtime/actions"
node_id=""
node_name=""
prompt=""
session_key="cli:verification"
markdown="false"
include_logs="false"

json_or_null() {
  local raw="$1"
  if [[ -z "$raw" ]]; then
    printf 'null'
  else
    python3 - "$raw" <<'PY'
import json
import sys
print(json.dumps(sys.argv[1]))
PY
  fi
}

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
    --node-id)
      node_id="$2"
      shift 2
      ;;
    --node-name)
      node_name="$2"
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
      markdown="true"
      shift
      ;;
    --include-logs)
      include_logs="true"
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

if [[ -z "$prompt" ]]; then
  echo "--prompt is required" >&2
  exit 1
fi

if [[ -z "$node_id" && -z "$node_name" ]]; then
  echo "--node-id or --node-name is required" >&2
  exit 1
fi

payload_file="$(mktemp)"
response_file="$(mktemp)"
trap 'rm -f "$payload_file" "$response_file"' EXIT

cat > "$payload_file" <<JSON
{
  "action": "invoke_prompt",
  "node_id": $(json_or_null "$node_id"),
  "node_name": $(json_or_null "$node_name"),
  "prompt": $(json_or_null "$prompt"),
  "session_key": $(json_or_null "$session_key"),
  "markdown": $markdown,
  "include_logs": $include_logs
}
JSON

url="${kernel_url%/}${endpoint}"
health_url="${kernel_url%/}/healthz"

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN runtime request: POST $url"
  cat "$payload_file"
  exit 0
fi

if ! curl --silent --fail "$health_url" >/dev/null 2>&1; then
  echo "OmniClaw kernel is not reachable at $health_url." >&2
  echo "Start it with: uv run python main.py" >&2
  exit 7
fi

http_code="$(
  curl --silent --show-error \
    --output "$response_file" \
    --write-out "%{http_code}" \
    -X POST \
    -H 'Content-Type: application/json' \
    --data-binary "@$payload_file" \
    "$url"
)"

if [[ "$http_code" -ge 400 ]]; then
  cat "$response_file" >&2
  echo >&2
  exit 22
fi

cat "$response_file"
echo
