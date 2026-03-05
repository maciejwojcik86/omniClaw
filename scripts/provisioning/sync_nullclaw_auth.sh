#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  sync_nullclaw_auth.sh [--apply] --source-user <user> --target-user <user> [--auth-filename <name>]

Default mode is dry-run. Use --apply to execute.
USAGE
}

dry_run=1
source_user=""
target_user=""
auth_filename="auth.json"

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
    --source-user)
      source_user="$2"
      shift 2
      ;;
    --target-user)
      target_user="$2"
      shift 2
      ;;
    --auth-filename)
      auth_filename="$2"
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

if [[ -z "$source_user" || -z "$target_user" ]]; then
  echo "--source-user and --target-user are required" >&2
  usage
  exit 1
fi

if ! id "$source_user" >/dev/null 2>&1; then
  echo "Source user '$source_user' does not exist" >&2
  exit 1
fi
if ! id "$target_user" >/dev/null 2>&1; then
  echo "Target user '$target_user' does not exist" >&2
  exit 1
fi

source_home="$(getent passwd "$source_user" | cut -d: -f6)"
target_home="$(getent passwd "$target_user" | cut -d: -f6)"

if [[ -z "$source_home" || -z "$target_home" ]]; then
  echo "Could not resolve user homes for '$source_user' or '$target_user'" >&2
  exit 1
fi

source_auth="$source_home/.nullclaw/$auth_filename"
target_nullclaw_dir="$target_home/.nullclaw"
target_auth="$target_nullclaw_dir/$auth_filename"

if [[ ! -f "$source_auth" ]]; then
  echo "Source auth file not found: $source_auth" >&2
  exit 1
fi

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN mode. Use --apply to sync auth."
fi

run_cmd install -d -m 0750 "$target_nullclaw_dir"
run_cmd cp "$source_auth" "$target_auth"
run_cmd chown "$target_user:$target_user" "$target_auth"
run_cmd chmod 600 "$target_auth"

if [[ "$dry_run" -eq 0 ]]; then
  echo "Synced auth file: $source_auth -> $target_auth"
fi
