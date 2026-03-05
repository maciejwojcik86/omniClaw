#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  grant_passwordless_sudo.sh [--apply] --username <user>

Default mode is dry-run. Use --apply to execute.
Requires root or helper env vars for non-root execution:
  OMNICLAW_PROVISIONING_HELPER_PATH
  OMNICLAW_PROVISIONING_HELPER_USE_SUDO=true
USAGE
}

dry_run=1
username=""
helper_path="${OMNICLAW_PROVISIONING_HELPER_PATH:-}"
helper_use_sudo="${OMNICLAW_PROVISIONING_HELPER_USE_SUDO:-false}"

helper_cmd() {
  local action="$1"
  shift
  local command=()
  if [[ -z "$helper_path" ]]; then
    echo "No provisioning helper configured." >&2
    exit 1
  fi
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

if [[ ! "$username" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]]; then
  echo "Invalid username: $username" >&2
  exit 1
fi

sudoers_file="/etc/sudoers.d/omniclaw-${username}-nopasswd"

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN: grant passwordless sudo for user '$username'"
  echo "DRY-RUN: target sudoers file '$sudoers_file'"
  if [[ "$(id -u)" -ne 0 && -n "$helper_path" ]]; then
    echo "DRY-RUN note: apply mode will use provisioning helper '$helper_path' because current user is non-root."
  fi
  exit 0
fi

if [[ "$(id -u)" -eq 0 ]]; then
  tmp_file="$(mktemp)"
  trap 'rm -f "$tmp_file"' EXIT
  printf '%s ALL=(ALL:ALL) NOPASSWD: ALL\n' "$username" > "$tmp_file"
  chown root:root "$tmp_file"
  chmod 0440 "$tmp_file"
  visudo -cf "$tmp_file"
  install -o root -g root -m 0440 "$tmp_file" "$sudoers_file"
  visudo -cf "$sudoers_file"
  su -s /bin/bash -c 'sudo -n id -u' "$username"
  rm -f "$tmp_file"
  trap - EXIT
else
  helper_cmd grant_passwordless_sudo "$username"
  helper_cmd verify_passwordless_sudo "$username"
fi

echo "Passwordless sudo verified for '$username'."
