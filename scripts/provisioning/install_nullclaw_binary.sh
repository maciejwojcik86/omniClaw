#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  install_nullclaw_binary.sh [--apply] --username <user> [--shared-binary-path <path-or-command>] [--target-name <name>]

Default mode is dry-run. Use --apply to execute.
USAGE
}

dry_run=1
username=""
shared_binary_path="/opt/omniclaw/bin/nullclaw"
target_name="nullclaw"
helper_path="${OMNICLAW_PROVISIONING_HELPER_PATH:-}"
helper_use_sudo="${OMNICLAW_PROVISIONING_HELPER_USE_SUDO:-false}"

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
    --username)
      username="$2"
      shift 2
      ;;
    --shared-binary-path)
      shared_binary_path="$2"
      shift 2
      ;;
    --binary-path)
      # Backward-compatible alias.
      shared_binary_path="$2"
      shift 2
      ;;
    --target-name)
      target_name="$2"
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

if [[ -z "$username" ]]; then
  echo "--username is required" >&2
  usage
  exit 1
fi

if ! id "$username" >/dev/null 2>&1; then
  if [[ "$dry_run" -eq 1 ]]; then
    owner_home="/home/$username"
    echo "DRY-RUN note: user '$username' does not exist yet, assuming home '$owner_home'."
  else
    echo "User '$username' does not exist" >&2
    exit 1
  fi
else
  owner_home="$(getent passwd "$username" | cut -d: -f6)"
  if [[ -z "$owner_home" ]]; then
    echo "Could not resolve home for '$username'" >&2
    exit 1
  fi
  if [[ ! -d "$owner_home" && "$dry_run" -eq 0 ]]; then
    echo "Resolved home does not exist for '$username': $owner_home" >&2
    exit 1
  fi
fi

resolved_shared_bin=""
if [[ -x "$shared_binary_path" ]]; then
  resolved_shared_bin="$shared_binary_path"
elif command -v "$shared_binary_path" >/dev/null 2>&1; then
  resolved_shared_bin="$(command -v "$shared_binary_path")"
fi

if [[ -z "$resolved_shared_bin" ]]; then
  if [[ "$dry_run" -eq 1 ]]; then
    resolved_shared_bin="$shared_binary_path"
    echo "DRY-RUN note: shared binary '$shared_binary_path' not found yet, assuming it exists when applied."
  else
    echo "Could not resolve shared nullclaw binary from '$shared_binary_path'" >&2
    echo "Hint: install shared binary first or pass --shared-binary-path /abs/path/to/nullclaw" >&2
    exit 1
  fi
fi

target_dir="$owner_home/.local/bin"
target_path="$target_dir/$target_name"

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN: install -d -m 0755 '$target_dir'"
  echo "DRY-RUN: rm -f '$target_path'"
  echo "DRY-RUN: ln -s '$resolved_shared_bin' '$target_path'"
  echo "DRY-RUN: chown '$username:$username' '$target_dir'"
  echo "DRY-RUN: chown -h '$username:$username' '$target_path'"
  if [[ "$(id -u)" -ne 0 && -n "$helper_path" ]]; then
    echo "DRY-RUN note: apply mode will use provisioning helper '$helper_path' because current user is non-root."
  fi
  exit 0
fi

if [[ "$(id -u)" -eq 0 ]]; then
  install -d -m 0755 "$target_dir"
  rm -f "$target_path"
  ln -s "$resolved_shared_bin" "$target_path"
  chown "$username:$username" "$target_dir"
  chown -h "$username:$username" "$target_path"
else
  helper_cmd install_user_nullclaw_link "$username" "$resolved_shared_bin" "$target_name"
fi

echo "Linked user nullclaw binary: $target_path -> $resolved_shared_bin"
