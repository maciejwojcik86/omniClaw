#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  trigger_budget_action.sh [--apply] [--kernel-url <url>] [--endpoint <path>] --action <action>
                           [--actor-node-id <id>] [--actor-node-name <name>]
                           [--node-id <id>] [--node-name <name>]
                           [--budget-mode <metered|free>]
                           [--new-daily-limit-usd <usd>]
                           [--allocations-file <json-file>]
                           [--reason <text>] [--impact-summary <text>]
                           [--cycle-date <YYYY-MM-DD>] [--break-glass]

Default mode is dry-run. Use --apply to execute HTTP POST.
Actions: sync_all_costs, sync_node_cost, update_node_allowance, team_budget_view,
         set_team_allocations, set_node_budget_mode, run_budget_cycle, recalculate_subtree,
         budget_report
USAGE
}

dry_run=1
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
endpoint="/v1/budgets/actions"
action=""
actor_node_id=""
actor_node_name=""
node_id=""
node_name=""
budget_mode=""
new_daily_limit_usd=""
allocations_file=""
reason=""
impact_summary=""
cycle_date=""
break_glass="false"

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
    --node-id)
      node_id="$2"
      shift 2
      ;;
    --node-name)
      node_name="$2"
      shift 2
      ;;
    --budget-mode)
      budget_mode="$2"
      shift 2
      ;;
    --new-daily-limit-usd)
      new_daily_limit_usd="$2"
      shift 2
      ;;
    --allocations-file)
      allocations_file="$2"
      shift 2
      ;;
    --reason)
      reason="$2"
      shift 2
      ;;
    --impact-summary)
      impact_summary="$2"
      shift 2
      ;;
    --cycle-date)
      cycle_date="$2"
      shift 2
      ;;
    --break-glass)
      break_glass="true"
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

if [[ -z "$action" ]]; then
  echo "--action is required" >&2
  usage
  exit 1
fi

case "$action" in
  sync_all_costs|sync_node_cost|update_node_allowance|team_budget_view|set_team_allocations|set_node_budget_mode|run_budget_cycle|recalculate_subtree|budget_report)
    ;;
  *)
    echo "Invalid --action '$action'" >&2
    usage
    exit 1
    ;;
esac

payload_file="$(mktemp)"
response_file="$(mktemp)"
trap 'rm -f "$payload_file" "$response_file"' EXIT

allocations_json="null"
if [[ -n "$allocations_file" ]]; then
  if [[ ! -f "$allocations_file" ]]; then
    echo "--allocations-file '$allocations_file' not found" >&2
    exit 1
  fi
  allocations_json="$(cat "$allocations_file")"
fi

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

cat > "$payload_file" <<JSON
{
  "action": "$action",
  "actor_node_id": $(json_or_null "$actor_node_id"),
  "actor_node_name": $(json_or_null "$actor_node_name"),
  "node_id": $(json_or_null "$node_id"),
  "node_name": $(json_or_null "$node_name"),
  "budget_mode": $(json_or_null "$budget_mode"),
  "new_daily_limit_usd": $(json_or_null "$new_daily_limit_usd"),
  "allocations": $allocations_json,
  "reason": $(json_or_null "$reason"),
  "impact_summary": $(json_or_null "$impact_summary"),
  "cycle_date": $(json_or_null "$cycle_date"),
  "break_glass": $break_glass
}
JSON

url="${kernel_url%/}${endpoint}"
health_url="${kernel_url%/}/healthz"

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN budget request: POST $url"
  cat "$payload_file"
  exit 0
fi

if ! curl --silent --fail "$health_url" >/dev/null 2>&1; then
  echo "OmniClaw kernel is not reachable at $health_url." >&2
  echo "Start it with: uv run omniclaw" >&2
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
curl_status=$?

if [[ "$curl_status" -ne 0 ]]; then
  exit "$curl_status"
fi

if [[ "$http_code" -ge 400 ]]; then
  cat "$response_file" >&2
  echo >&2
  exit 22
fi

cat "$response_file"
echo
