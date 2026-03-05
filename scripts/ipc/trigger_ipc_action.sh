#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  trigger_ipc_action.sh [--apply] [--kernel-url <url>] [--endpoint <path>]
                        [--action <scan_forms|scan_messages>] [--limit <n>]

Default mode is dry-run. Use --apply to execute HTTP POST.
USAGE
}

dry_run=1
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
endpoint="/v1/ipc/actions"
action="scan_forms"
limit="200"

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
    --limit)
      limit="$2"
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

case "$action" in
  scan_forms|scan_messages)
    ;;
  *)
    echo "Invalid --action '$action'" >&2
    usage
    exit 1
    ;;
esac

if ! [[ "$limit" =~ ^[0-9]+$ ]]; then
  echo "--limit must be an integer" >&2
  exit 1
fi

payload_file="$(mktemp)"
trap 'rm -f "$payload_file"' EXIT

cat > "$payload_file" <<JSON
{
  "action": "$action",
  "limit": $limit
}
JSON

url="${kernel_url%/}${endpoint}"

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN ipc request: POST $url"
  cat "$payload_file"
  exit 0
fi

curl --fail --show-error --silent \
  -X POST \
  -H 'Content-Type: application/json' \
  --data-binary "@$payload_file" \
  "$url"

echo
