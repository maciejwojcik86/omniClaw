#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  trigger_skill_action.sh [--apply] [--kernel-url <url>] [--endpoint <path>] --action <action>
                          [--actor-node-id <id>] [--actor-node-name <name>]
                          [--target-node-id <id>] [--target-node-name <name>]
                          [--skill-name <name>] [--skill-names <csv>]
                          [--lifecycle-status <DRAFT|ACTIVE|DEACTIVATED>]
                          [--source-path <dir>] [--description <text>] [--version <ver>]
                          [--sync-scope <target|all_active_agents>]

Default mode is dry-run. Use --apply to execute HTTP POST.
Actions: list_master_skills, list_active_master_skills, draft_master_skill, update_master_skill,
         set_master_skill_status, list_agent_skill_assignments, assign_master_skills,
         remove_master_skills, sync_agent_skills
USAGE
}

dry_run=1
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
endpoint="/v1/skills/actions"
action=""
actor_node_id=""
actor_node_name=""
target_node_id=""
target_node_name=""
skill_name=""
skill_names=""
lifecycle_status=""
source_path=""
description=""
version=""
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
    --skill-name)
      skill_name="$2"
      shift 2
      ;;
    --skill-names)
      skill_names="$2"
      shift 2
      ;;
    --lifecycle-status)
      lifecycle_status="$2"
      shift 2
      ;;
    --source-path)
      source_path="$2"
      shift 2
      ;;
    --description)
      description="$2"
      shift 2
      ;;
    --version)
      version="$2"
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

case "$sync_scope" in
  target|all_active_agents)
    ;;
  *)
    echo "Invalid --sync-scope '$sync_scope'" >&2
    exit 1
    ;;
esac

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

skill_names_json="$(
  python3 - "$skill_names" <<'PY'
import json
import sys

raw = sys.argv[1]
if not raw.strip():
    print("[]")
else:
    items = [item.strip() for item in raw.split(",") if item.strip()]
    print(json.dumps(items))
PY
)"

payload_file="$(mktemp)"
trap 'rm -f "$payload_file"' EXIT

cat > "$payload_file" <<JSON
{
  "action": "$action",
  "actor_node_id": $(json_or_null "$actor_node_id"),
  "actor_node_name": $(json_or_null "$actor_node_name"),
  "target_node_id": $(json_or_null "$target_node_id"),
  "target_node_name": $(json_or_null "$target_node_name"),
  "skill_name": $(json_or_null "$skill_name"),
  "skill_names": $skill_names_json,
  "lifecycle_status": $(json_or_null "$lifecycle_status"),
  "source_path": $(json_or_null "$source_path"),
  "description": $(json_or_null "$description"),
  "version": $(json_or_null "$version"),
  "sync_scope": "$sync_scope"
}
JSON

url="${kernel_url%/}${endpoint}"

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN skills request: POST $url"
  cat "$payload_file"
  exit 0
fi

curl --fail --show-error --silent \
  -X POST \
  -H 'Content-Type: application/json' \
  --data-binary "@$payload_file" \
  "$url"

echo
