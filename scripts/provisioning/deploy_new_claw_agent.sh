#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  deploy_new_claw_agent.sh [--apply] --username <name> --node-name <node> --manager-group <group>
                         [--workspace-root <path>] [--shell <path>] [--uid <uid>]
                         [--shared-nullclaw-binary <path-or-command>] [--bootstrap-shared-binary-from <path-or-command>]
                         [--shared-install-root <path>] [--shared-version <version>]
                         [--manager-name <name>]
                         [--role-name <role>] [--agents-source-file <path>]

Default mode is dry-run. Use --apply to execute.
USAGE
}

dry_run=1
username=""
node_name=""
manager_group=""
workspace_root=""
shell_path="/usr/sbin/nologin"
uid_value=""
shared_nullclaw_binary="/opt/omniclaw/bin/nullclaw"
bootstrap_shared_binary_from=""
shared_install_root="/opt/omniclaw"
shared_version=""
manager_name="Human Supervisor"
role_name="Worker Agent"
agents_source_file=""

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
    --node-name)
      node_name="$2"
      shift 2
      ;;
    --manager-group)
      manager_group="$2"
      shift 2
      ;;
    --workspace-root)
      workspace_root="$2"
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
    --shared-nullclaw-binary)
      shared_nullclaw_binary="$2"
      shift 2
      ;;
    --nullclaw-binary)
      # Backward-compatible alias.
      shared_nullclaw_binary="$2"
      shift 2
      ;;
    --bootstrap-shared-binary-from)
      bootstrap_shared_binary_from="$2"
      shift 2
      ;;
    --shared-install-root)
      shared_install_root="$2"
      shift 2
      ;;
    --shared-version)
      shared_version="$2"
      shift 2
      ;;
    --manager-name)
      manager_name="$2"
      shift 2
      ;;
    --role-name)
      role_name="$2"
      shift 2
      ;;
    --agents-source-file)
      agents_source_file="$2"
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

if [[ -z "$username" || -z "$node_name" || -z "$manager_group" ]]; then
  echo "--username, --node-name, and --manager-group are required" >&2
  usage
  exit 1
fi

if [[ -z "$workspace_root" ]]; then
  workspace_root="/home/$username/.nullclaw/workspace"
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

if [[ -n "$bootstrap_shared_binary_from" ]]; then
  shared_cmd=(
    "$ROOT/scripts/provisioning/install_shared_nullclaw_binary.sh"
    "${apply_flag[@]}"
    --binary-path "$bootstrap_shared_binary_from"
    --install-root "$shared_install_root"
  )
  if [[ -n "$shared_version" ]]; then
    shared_cmd+=(--version "$shared_version")
  fi
  "${shared_cmd[@]}"
  shared_nullclaw_binary="$shared_install_root/bin/nullclaw"
fi

"$ROOT/scripts/provisioning/install_nullclaw_binary.sh" "${apply_flag[@]}" --username "$username" --shared-binary-path "$shared_nullclaw_binary"
uv run python "$ROOT/scripts/provisioning/init_nullclaw_config.py" "${apply_flag[@]}" --username "$username"
uv run python "$ROOT/scripts/provisioning/create_workspace_tree.py" "${apply_flag[@]}" --workspace-root "$workspace_root"
"$ROOT/scripts/provisioning/apply_workspace_permissions.sh" "${apply_flag[@]}" --owner-user "$username" --manager-group "$manager_group" --workspace-root "$workspace_root"
# Re-run scaffold after permissions so non-root callers can create any missing
# workspace files even when the first pass had to use privileged helper fallback.
uv run python "$ROOT/scripts/provisioning/create_workspace_tree.py" "${apply_flag[@]}" --workspace-root "$workspace_root"
agents_cmd=(
  uv run python "$ROOT/scripts/provisioning/write_agent_instructions.py" "${apply_flag[@]}"
  --workspace-root "$workspace_root"
  --node-name "$node_name"
  --manager-name "$manager_name"
  --role-name "$role_name"
)
if [[ -n "$agents_source_file" ]]; then
  agents_cmd+=(--source-file "$agents_source_file")
fi
"${agents_cmd[@]}"

echo "Deploy workflow complete."
