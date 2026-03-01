#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

dry_run=1
username=""
workspace_root=""
manager_group=""
shell_path="/usr/sbin/nologin"
uid_value=""

usage() {
  cat <<'USAGE'
Usage:
  provision_agent_workflow.sh [--apply] --username <name> --workspace-root <path> --manager-group <group> [--shell <path>] [--uid <uid>]

Default mode is dry-run. Use --apply to execute.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      dry_run=0
      shift
      ;;
    --username)
      username="$2"
      shift 2
      ;;
    --workspace-root)
      workspace_root="$2"
      shift 2
      ;;
    --manager-group)
      manager_group="$2"
      shift 2
      ;;
    --shell)
      shell_path="$2"
      shift 2
      ;;
    --uid)
      uid_value="$2"
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

if [[ -z "$username" || -z "$workspace_root" || -z "$manager_group" ]]; then
  echo "--username, --workspace-root, and --manager-group are required" >&2
  usage
  exit 1
fi

apply_flag=()
if [[ "$dry_run" -eq 0 ]]; then
  apply_flag=(--apply)
fi

user_cmd=("$ROOT/scripts/provisioning/create_linux_user.sh" "${apply_flag[@]}" --username "$username" --shell "$shell_path")
if [[ -n "$uid_value" ]]; then
  user_cmd+=(--uid "$uid_value")
fi
"${user_cmd[@]}"
uv run python "$ROOT/scripts/provisioning/create_workspace_tree.py" "${apply_flag[@]}" --workspace-root "$workspace_root"
"$ROOT/scripts/provisioning/apply_workspace_permissions.sh" "${apply_flag[@]}" --owner-user "$username" --manager-group "$manager_group" --workspace-root "$workspace_root"

echo "Workflow complete."
