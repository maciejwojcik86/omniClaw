#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  trigger_kernel_action.sh [--apply] [--kernel-url <url>] [--endpoint <path>] --payload-file <json>

Default mode is dry-run. Use --apply to execute HTTP POST.
USAGE
}

dry_run=1
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
endpoint="/v1/provisioning/actions"
payload_file=""

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
    --payload-file)
      payload_file="$2"
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

if [[ -z "$payload_file" ]]; then
  echo "--payload-file is required" >&2
  usage
  exit 1
fi

if [[ ! -f "$payload_file" ]]; then
  echo "Payload file '$payload_file' not found" >&2
  exit 1
fi

url="${kernel_url%/}${endpoint}"

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN kernel request: POST $url"
  echo "DRY-RUN payload file: $payload_file"
  exit 0
fi

curl --fail --show-error --silent \
  -X POST \
  -H 'Content-Type: application/json' \
  --data-binary "@$payload_file" \
  "$url"

echo
echo "Kernel action request sent to $url"
