#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  create_linux_user.sh [--apply] --username <name> [--home-dir <path>] [--uid <uid>] [--shell <path>]

Default mode is dry-run. Use --apply to execute.
USAGE
}

dry_run=1
username=""
home_dir=""
uid_value=""
shell_path="/usr/sbin/nologin"

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
    --home-dir)
      home_dir="$2"
      shift 2
      ;;
    --uid)
      uid_value="$2"
      shift 2
      ;;
    --shell)
      shell_path="$2"
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

if [[ -z "$home_dir" ]]; then
  home_dir="/home/$username"
fi

if id "$username" >/dev/null 2>&1; then
  echo "User '$username' already exists; no action needed."
  exit 0
fi

cmd=(useradd -m -U -d "$home_dir" -s "$shell_path")
if [[ -n "$uid_value" ]]; then
  if [[ ! "$uid_value" =~ ^[0-9]+$ ]]; then
    echo "--uid must be numeric" >&2
    exit 1
  fi
  cmd+=(-u "$uid_value")
fi
cmd+=("$username")

if [[ "$dry_run" -eq 1 ]]; then
  printf "DRY-RUN user creation command:"
  printf " %q" "${cmd[@]}"
  printf "\n"
  exit 0
fi

"${cmd[@]}"
echo "Created user '$username' with home '$home_dir' and shell '$shell_path'."
