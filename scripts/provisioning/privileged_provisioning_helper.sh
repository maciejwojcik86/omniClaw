#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  privileged_provisioning_helper.sh <action> [args]

Actions:
  id_uid <username>
  create_user <username> <home_dir> <shell> [uid]
  add_groups <username> <group_csv>
  create_workspace <workspace_root>
  apply_permissions <owner_user> <manager_group> <workspace_root>
USAGE
}

require_username() {
  local value="$1"
  [[ "$value" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] || {
    echo "Invalid username: $value" >&2
    exit 2
  }
}

require_group_csv() {
  local value="$1"
  [[ "$value" =~ ^[a-z_][a-z0-9_-]{0,31}(,[a-z_][a-z0-9_-]{0,31})*$ ]] || {
    echo "Invalid group list: $value" >&2
    exit 2
  }
}

require_abs_path() {
  local value="$1"
  [[ "$value" == /* ]] || {
    echo "Path must be absolute: $value" >&2
    exit 2
  }
}

create_workspace_tree() {
  local root="$1"
  mkdir -p "$root/inbox/unread"
  mkdir -p "$root/inbox/read"
  mkdir -p "$root/outbox/pending"
  mkdir -p "$root/outbox/drafts"
  mkdir -p "$root/outbox/sent"
  mkdir -p "$root/notes"
  mkdir -p "$root/journal"
  mkdir -p "$root/metrics"
  mkdir -p "$root/drafts"
  mkdir -p "$root/skills"

  [[ -f "$root/notes/TODO.md" ]] || printf '# TODO\n\n- [ ] Add first task\n' > "$root/notes/TODO.md"
  [[ -f "$root/notes/DECISIONS.md" ]] || printf '# Decisions\n\n' > "$root/notes/DECISIONS.md"
  [[ -f "$root/notes/BLOCKERS.md" ]] || printf '# Blockers\n\n' > "$root/notes/BLOCKERS.md"
  [[ -f "$root/metrics/KPI.csv" ]] || printf 'date,metric,value\n' > "$root/metrics/KPI.csv"
  [[ -f "$root/persona_template.md" ]] || printf '# Persona Template\n\n' > "$root/persona_template.md"
  [[ -f "$root/AGENTS.md" ]] || printf '# AGENTS\n\nRendered by kernel context injector.\n' > "$root/AGENTS.md"
}

action="${1:-}"
if [[ -z "$action" ]]; then
  usage
  exit 1
fi
shift || true

case "$action" in
  id_uid)
    username="${1:-}"
    require_username "$username"
    id -u "$username"
    ;;

  create_user)
    username="${1:-}"
    home_dir="${2:-}"
    shell_path="${3:-}"
    uid_value="${4:-}"

    require_username "$username"
    require_abs_path "$home_dir"
    require_abs_path "$shell_path"

    if id "$username" >/dev/null 2>&1; then
      exit 0
    fi

    cmd=(useradd -m -U -d "$home_dir" -s "$shell_path")
    if [[ -n "$uid_value" ]]; then
      [[ "$uid_value" =~ ^[0-9]+$ ]] || {
        echo "UID must be numeric" >&2
        exit 2
      }
      cmd+=(-u "$uid_value")
    fi
    cmd+=("$username")
    "${cmd[@]}"
    ;;

  add_groups)
    username="${1:-}"
    group_csv="${2:-}"
    require_username "$username"
    require_group_csv "$group_csv"
    usermod -aG "$group_csv" "$username"
    ;;

  create_workspace)
    workspace_root="${1:-}"
    require_abs_path "$workspace_root"
    create_workspace_tree "$workspace_root"
    ;;

  apply_permissions)
    owner_user="${1:-}"
    manager_group="${2:-}"
    workspace_root="${3:-}"

    require_username "$owner_user"
    require_group_csv "$manager_group"
    require_abs_path "$workspace_root"
    [[ -d "$workspace_root" ]] || {
      echo "Workspace root does not exist: $workspace_root" >&2
      exit 2
    }
    home_root="$(dirname "$workspace_root")"
    [[ -d "$home_root" ]] || {
      echo "Home root does not exist: $home_root" >&2
      exit 2
    }

    chown "$owner_user:$manager_group" "$home_root"
    chmod u=rwx,g=rx,o= "$home_root"
    chown -R "$owner_user:$manager_group" "$workspace_root"
    chmod -R u=rwX,g=rwX,o= "$workspace_root"
    find "$workspace_root" -type d -exec chmod g+s {} +
    ;;

  *)
    usage
    exit 1
    ;;
esac
