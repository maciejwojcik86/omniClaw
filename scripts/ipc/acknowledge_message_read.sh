#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  acknowledge_message_read.sh [--apply] [--kernel-url <url>] [--endpoint <path>]
                              --workspace-root <path> --form-file <name>
                              --form-id <form-id> --actor-node-id <node-id>
                              [--decision-key <decision>]

Default mode is dry-run. With --apply, the script:
1) moves inbox/unread/<form-file> -> inbox/read/<form-file>
2) calls forms endpoint action transition_form
USAGE
}

dry_run=1
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
endpoint="/v1/forms/actions"
workspace_root=""
form_file=""
form_id=""
actor_node_id=""
decision_key="acknowledge_read"

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
    --workspace-root)
      workspace_root="$2"
      shift 2
      ;;
    --form-file)
      form_file="$2"
      shift 2
      ;;
    --form-id)
      form_id="$2"
      shift 2
      ;;
    --actor-node-id)
      actor_node_id="$2"
      shift 2
      ;;
    --decision-key)
      decision_key="$2"
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

if [[ -z "$workspace_root" || -z "$form_file" || -z "$form_id" || -z "$actor_node_id" ]]; then
  echo "--workspace-root, --form-file, --form-id, and --actor-node-id are required" >&2
  usage
  exit 1
fi

unread_path="${workspace_root%/}/inbox/unread/${form_file}"
read_dir="${workspace_root%/}/inbox/read"
read_path="${read_dir}/${form_file}"

payload_file="$(mktemp)"
trap 'rm -f "$payload_file"' EXIT

cat > "$payload_file" <<JSON
{
  "action": "transition_form",
  "form_id": "$form_id",
  "actor_node_id": "$actor_node_id",
  "decision_key": "$decision_key",
  "payload": {
    "unread_path": "$unread_path",
    "read_path": "$read_path"
  }
}
JSON

url="${kernel_url%/}${endpoint}"

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN move: $unread_path -> $read_path"
  echo "DRY-RUN forms request: POST $url"
  cat "$payload_file"
  exit 0
fi

if [[ ! -f "$unread_path" ]]; then
  echo "unread form file not found: $unread_path" >&2
  exit 1
fi

mkdir -p "$read_dir"
mv "$unread_path" "$read_path"

curl --fail --show-error --silent \
  -X POST \
  -H 'Content-Type: application/json' \
  --data-binary "@$payload_file" \
  "$url"

echo
