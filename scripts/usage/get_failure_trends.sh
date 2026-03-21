#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  get_failure_trends.sh [--apply] [--kernel-url <url>] [--endpoint <path>]
                        [--provider <provider>] [--model <model>] [--limit <n>]

Default mode is dry-run. Use --apply to execute HTTP GET.
USAGE
}

dry_run=1
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
endpoint="/v1/usage/failure-trends"
provider=""
model=""
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
    --provider)
      provider="$2"
      shift 2
      ;;
    --model)
      model="$2"
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

python3 - "$kernel_url" "$endpoint" "$provider" "$model" "$limit" "$dry_run" <<'PY'
import sys
import urllib.error
import urllib.parse
import urllib.request

kernel_url, endpoint, provider, model, limit, dry_run = sys.argv[1:7]
params = []
if provider:
    params.append(("provider", provider))
if model:
    params.append(("model", model))
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
