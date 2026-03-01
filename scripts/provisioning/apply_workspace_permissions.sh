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

run_cmd() {
  if [[ "$dry_run" -eq 1 ]]; then
    printf "DRY-RUN:"
    printf " %q" "$@"
    printf "\n"
  else
    "$@"
  fi
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

if ! id "$owner_user" >/dev/null 2>&1; then
  echo "Owner user '$owner_user' does not exist" >&2
  exit 1
fi

if ! getent group "$manager_group" >/dev/null 2>&1; then
  echo "Manager group '$manager_group' does not exist" >&2
  exit 1
fi

if [[ ! -d "$workspace_root" ]]; then
  echo "Workspace root '$workspace_root' does not exist" >&2
  exit 1
fi

owner_home="$(getent passwd "$owner_user" | cut -d: -f6)"
if [[ -z "$owner_home" || ! -d "$owner_home" ]]; then
  echo "Owner home '$owner_home' does not exist" >&2
  exit 1
fi

workspace_parent="$(dirname "$workspace_root")"
if [[ ! -d "$workspace_parent" ]]; then
  echo "Workspace parent '$workspace_parent' does not exist" >&2
  exit 1
fi

run_cmd chown "$owner_user:$manager_group" "$owner_home"
run_cmd chmod u=rwx,g=rx,o= "$owner_home"
if [[ "$workspace_parent" != "$owner_home" ]]; then
  run_cmd chown "$owner_user:$manager_group" "$workspace_parent"
  run_cmd chmod u=rwx,g=rx,o= "$workspace_parent"
fi
run_cmd chown -R "$owner_user:$manager_group" "$workspace_root"
run_cmd chmod -R u=rwX,g=rwX,o= "$workspace_root"
run_cmd find "$workspace_root" -type d -exec chmod g+s {} +

if [[ "$dry_run" -eq 0 ]]; then
  echo "Applied ownership and permissions on '$workspace_root'."
fi
