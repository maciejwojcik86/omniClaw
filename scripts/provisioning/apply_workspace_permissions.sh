#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  apply_workspace_permissions.sh [--apply] --owner-user <user> --manager-group <group> --workspace-root <path>

Default mode is dry-run. Use --apply to execute.
USAGE
}

dry_run=1
owner_user=""
manager_group=""
workspace_root=""
helper_path="${OMNICLAW_PROVISIONING_HELPER_PATH:-}"
helper_use_sudo="${OMNICLAW_PROVISIONING_HELPER_USE_SUDO:-false}"

run_cmd() {
  if [[ "$dry_run" -eq 1 ]]; then
    printf "DRY-RUN:"
    printf " %q" "$@"
    printf "\n"
  else
    "$@"
  fi
}

helper_cmd() {
  local action="$1"
  shift
  local command=()
  if [[ -n "$helper_path" ]]; then
    if [[ ! -x "$helper_path" ]]; then
      echo "Configured provisioning helper is not executable: $helper_path" >&2
      exit 1
    fi
    if [[ "${helper_use_sudo,,}" == "true" || "$helper_use_sudo" == "1" ]]; then
      command=(sudo -n "$helper_path" "$action" "$@")
    else
      command=("$helper_path" "$action" "$@")
    fi
    "${command[@]}"
    return
  fi
  echo "No provisioning helper configured." >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      dry_run=0
      shift
      ;;
    --owner-user)
      owner_user="$2"
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

if [[ -z "$owner_user" || -z "$manager_group" || -z "$workspace_root" ]]; then
  echo "--owner-user, --manager-group, and --workspace-root are required" >&2
  usage
  exit 1
fi

if id "$owner_user" >/dev/null 2>&1; then
  owner_home="$(getent passwd "$owner_user" | cut -d: -f6)"
else
  if [[ "$dry_run" -eq 1 ]]; then
    owner_home="/home/$owner_user"
    echo "DRY-RUN: owner user '$owner_user' does not exist yet; assuming home '$owner_home'."
  else
    echo "Owner user '$owner_user' does not exist" >&2
    exit 1
  fi
fi

if ! getent group "$manager_group" >/dev/null 2>&1; then
  if [[ "$dry_run" -eq 1 ]]; then
    echo "DRY-RUN: manager group '$manager_group' does not exist yet."
  else
    echo "Manager group '$manager_group' does not exist" >&2
    exit 1
  fi
fi

if [[ "$dry_run" -eq 0 && "$(id -u)" -ne 0 ]]; then
  helper_cmd apply_permissions "$owner_user" "$manager_group" "$workspace_root"
  echo "Applied ownership and permissions on '$workspace_root'."
  exit 0
fi

if [[ ! -d "$workspace_root" && "$dry_run" -eq 0 ]]; then
  echo "Workspace root '$workspace_root' does not exist" >&2
  exit 1
fi

if [[ -z "$owner_home" || ( ! -d "$owner_home" && "$dry_run" -eq 0 ) ]]; then
  echo "Owner home '$owner_home' does not exist" >&2
  exit 1
fi

workspace_parent="$(dirname "$workspace_root")"
if [[ ! -d "$workspace_parent" && "$dry_run" -eq 0 ]]; then
  echo "Workspace parent '$workspace_parent' does not exist" >&2
  exit 1
fi
config_path="$workspace_parent/config.json"

run_cmd chown "$owner_user:$manager_group" "$owner_home"
run_cmd chmod u=rwx,g=rx,o= "$owner_home"
if [[ "$workspace_parent" != "$owner_home" ]]; then
  run_cmd chown "$owner_user:$manager_group" "$workspace_parent"
  run_cmd chmod u=rwx,g=rx,o= "$workspace_parent"
fi
run_cmd chown -R "$owner_user:$manager_group" "$workspace_root"
run_cmd chmod -R u=rwX,g=rwX,o= "$workspace_root"
run_cmd find "$workspace_root" -type d -exec chmod g+s {} +
if [[ -f "$config_path" || "$dry_run" -eq 1 ]]; then
  run_cmd chown "$owner_user:$manager_group" "$config_path"
  run_cmd chmod u=rw,g=r,o= "$config_path"
fi

if [[ "$dry_run" -eq 0 ]]; then
  echo "Applied ownership and permissions on '$workspace_root'."
elif [[ "$(id -u)" -ne 0 && -n "$helper_path" ]]; then
  echo "DRY-RUN note: apply mode will use provisioning helper '$helper_path' because current user is non-root."
fi
