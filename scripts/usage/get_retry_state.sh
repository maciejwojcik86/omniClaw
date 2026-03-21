#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  get_retry_state.sh [--apply] [--kernel-url <url>] [--endpoint <path>]
                     [--node-id <id>] [--retry-status <status>] [--limit <n>]

Default mode is dry-run. Use --apply to execute HTTP GET.
USAGE
}

dry_run=1
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
endpoint="/v1/usage/retries"
node_id=""
retry_status=""
limit="50"

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
    --retry-status)
      retry_status="$2"
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

python3 - "$kernel_url" "$endpoint" "$node_id" "$retry_status" "$limit" "$dry_run" <<'PY'
import sys
import urllib.error
import urllib.parse
import urllib.request

kernel_url, endpoint, node_id, retry_status, limit, dry_run = sys.argv[1:7]
params = []
if node_id:
    params.append(("node_id", node_id))
if retry_status:
    params.append(("retry_status", retry_status))
if limit:
    params.append(("limit", limit))
query = urllib.parse.urlencode(params)
url = f"{kernel_url.rstrip('/')}{endpoint}"
if query:
    url = f"{url}?{query}"
if dry_run == "1":
    print(f"DRY-RUN usage request: GET {url}")
    raise SystemExit(0)
req = urllib.request.Request(url, headers={"Accept": "application/json"})
try:
    with urllib.request.urlopen(req) as resp:
        print(resp.read().decode())
except urllib.error.HTTPError as exc:
    sys.stderr.write(exc.read().decode() + "\n")
    raise SystemExit(22)
PY
