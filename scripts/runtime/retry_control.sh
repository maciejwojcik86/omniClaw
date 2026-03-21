#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  retry_control.sh [--apply] [--kernel-url <url>] --action <retry_now|cancel_retry> --task-key <key>

Examples:
  retry_control.sh --action retry_now --task-key invoke_prompt:node-123:cli:test
  retry_control.sh --apply --action cancel_retry --task-key invoke_prompt:node-123:cli:test
USAGE
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
apply_flag=""
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
action=""
task_key=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      apply_flag="--apply"
      shift
      ;;
    --kernel-url)
      kernel_url="$2"
      shift 2
      ;;
    --action)
      action="$2"
      shift 2
      ;;
    --task-key)
      task_key="$2"
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
  retry_now|cancel_retry)
    ;;
  *)
    echo "--action must be retry_now or cancel_retry" >&2
    usage
    exit 1
    ;;
esac

if [[ -z "$task_key" ]]; then
  echo "--task-key is required" >&2
  usage
  exit 1
fi

exec "$script_dir/trigger_runtime_action.sh" ${apply_flag:+$apply_flag} --kernel-url "$kernel_url" --action "$action" --task-key "$task_key"
