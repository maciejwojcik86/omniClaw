#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  trigger_instructions_action.sh [--apply] [--kernel-url <url>] [--endpoint <path>] --action <action>
                                 [--actor-node-id <id>] [--actor-node-name <name>]
                                 [--target-node-id <id>] [--target-node-name <name>]
                                 [--template-file <path>] [--sync-scope <target|all_active_agents>]

Default mode is dry-run. Use --apply to execute HTTP POST.
Actions: list_accessible_targets, get_template, preview_render, set_template, sync_render
USAGE
}

dry_run=1
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
endpoint="/v1/instructions/actions"
action=""
actor_node_id=""
actor_node_name=""
target_node_id=""
target_node_name=""
template_file=""
sync_scope="target"

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
    --actor-node-id)
      actor_node_id="$2"
      shift 2
      ;;
    --actor-node-name)
      actor_node_name="$2"
      shift 2
      ;;
    --target-node-id)
      target_node_id="$2"
      shift 2
      ;;
    --target-node-name)
      target_node_name="$2"
      shift 2
      ;;
    --template-file)
      template_file="$2"
      shift 2
      ;;
    --sync-scope)
      sync_scope="$2"
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
  list_accessible_targets|get_template|preview_render|set_template|sync_render)
    ;;
  *)
    echo "Invalid --action '$action'" >&2
    usage
    exit 1
    ;;
esac

case "$sync_scope" in
  target|all_active_agents)
    ;;
  *)
    echo "Invalid --sync-scope '$sync_scope'" >&2
    usage
    exit 1
    ;;
esac

payload_file="$(mktemp)"
trap 'rm -f "$payload_file"' EXIT

template_json="null"
if [[ -n "$template_file" ]]; then
  if [[ ! -f "$template_file" ]]; then
    echo "--template-file '$template_file' not found" >&2
    exit 1
  fi
  template_json="$(python3 - "$template_file" <<'PY'
from pathlib import Path
import json
import sys

print(json.dumps(Path(sys.argv[1]).read_text(encoding="utf-8")))
PY
)"
fi

actor_node_id_json="null"
actor_node_name_json="null"
target_node_id_json="null"
target_node_name_json="null"
if [[ -n "$actor_node_id" ]]; then
  actor_node_id_json="\"$actor_node_id\""
fi
if [[ -n "$actor_node_name" ]]; then
  actor_node_name_json="\"$actor_node_name\""
fi
if [[ -n "$target_node_id" ]]; then
  target_node_id_json="\"$target_node_id\""
fi
if [[ -n "$target_node_name" ]]; then
  target_node_name_json="\"$target_node_name\""
fi

cat > "$payload_file" <<JSON
{
  "action": "$action",
  "actor_node_id": $actor_node_id_json,
  "actor_node_name": $actor_node_name_json,
  "target_node_id": $target_node_id_json,
  "target_node_name": $target_node_name_json,
  "template_content": $template_json,
  "sync_scope": "$sync_scope"
}
JSON

url="${kernel_url%/}${endpoint}"

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN instructions request: POST $url"
  cat "$payload_file"
  exit 0
fi

curl --fail --show-error --silent \
  -X POST \
  -H 'Content-Type: application/json' \
  --data-binary "@$payload_file" \
  "$url"

echo
