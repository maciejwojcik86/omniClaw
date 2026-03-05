#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  smoke_form_workflows.sh [--apply] [--kernel-url <url>]

Publishes and (optionally) activates canonical workspace form workflows:
- message
- deploy_new_agent

Dry-run by default.
USAGE
}

dry_run=1
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"

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

apply_flag=()
if [[ "$dry_run" -eq 0 ]]; then
  apply_flag=(--apply)
fi

echo "[1/2] publish message workflow"
"$ROOT/scripts/forms/upsert_workflow_from_workspace.sh" \
  "${apply_flag[@]}" \
  --activate \
  --kernel-url "$kernel_url" \
  --form-type message

echo "[2/2] publish deploy_new_agent workflow"
"$ROOT/scripts/forms/upsert_workflow_from_workspace.sh" \
  "${apply_flag[@]}" \
  --activate \
  --kernel-url "$kernel_url" \
  --form-type deploy_new_agent

echo "Workflow smoke completed."
