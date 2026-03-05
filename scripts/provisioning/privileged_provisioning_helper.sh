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
  install_user_nullclaw_link <username> <shared_binary_path> [target_name]
  init_user_nullclaw_config <username> [force]
  apply_permissions <owner_user> <manager_group> <workspace_root>
  grant_passwordless_sudo <username>
  verify_passwordless_sudo <username>
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

require_existing_user() {
  local username="$1"
  require_username "$username"
  id "$username" >/dev/null 2>&1 || {
    echo "User does not exist: $username" >&2
    exit 2
  }
}

resolve_home_dir() {
  local username="$1"
  local home_dir
  home_dir="$(getent passwd "$username" | cut -d: -f6)"
  [[ -n "$home_dir" ]] || {
    echo "Could not resolve home for user: $username" >&2
    exit 2
  }
  echo "$home_dir"
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
init_config_script="$repo_root/scripts/provisioning/init_nullclaw_config.py"

create_workspace_tree() {
  local root="$1"
  mkdir -p "$root/inbox/unread"
  mkdir -p "$root/inbox/read"
  mkdir -p "$root/outbox/pending"
  mkdir -p "$root/outbox/drafts"
  mkdir -p "$root/outbox/archive"
  mkdir -p "$root/outbox/dead-letter"
  mkdir -p "$root/notes"
  mkdir -p "$root/metrics"
  mkdir -p "$root/drafts"
  mkdir -p "$root/skills"

  [[ -f "$root/notes/DECISIONS.md" ]] || printf '# Decisions\n\n' > "$root/notes/DECISIONS.md"
  [[ -f "$root/notes/BLOCKERS.md" ]] || printf '# Blockers\n\n' > "$root/notes/BLOCKERS.md"
  [[ -f "$root/metrics/KPI.csv" ]] || printf 'date,metric,value\n' > "$root/metrics/KPI.csv"
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

  install_user_nullclaw_link)
    username="${1:-}"
    shared_binary_path="${2:-}"
    target_name="${3:-nullclaw}"

    require_existing_user "$username"
    require_abs_path "$shared_binary_path"
    [[ -x "$shared_binary_path" ]] || {
      echo "Shared binary is not executable: $shared_binary_path" >&2
      exit 2
    }
    [[ "$target_name" =~ ^[A-Za-z0-9._-]+$ ]] || {
      echo "Invalid target name: $target_name" >&2
      exit 2
    }

    owner_home="$(resolve_home_dir "$username")"
    target_dir="$owner_home/.local/bin"
    target_path="$target_dir/$target_name"

    install -d -m 0755 "$target_dir"
    rm -f "$target_path"
    ln -s "$shared_binary_path" "$target_path"
    chown "$username:$username" "$target_dir"
    chown -h "$username:$username" "$target_path"
    ;;

  init_user_nullclaw_config)
    username="${1:-}"
    force_flag="${2:-}"
    require_existing_user "$username"
    [[ -f "$init_config_script" ]] || {
      echo "Missing config initializer: $init_config_script" >&2
      exit 2
    }
    init_cmd=(python3 "$init_config_script" --apply --username "$username")
    if [[ "$force_flag" == "force" ]]; then
      init_cmd+=(--force)
    fi
    "${init_cmd[@]}"
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
    owner_home="$(getent passwd "$owner_user" | cut -d: -f6)"
    [[ -n "$owner_home" && -d "$owner_home" ]] || {
      echo "Owner home does not exist: $owner_home" >&2
      exit 2
    }
    workspace_parent="$(dirname "$workspace_root")"
    [[ -d "$workspace_parent" ]] || {
      echo "Workspace parent does not exist: $workspace_parent" >&2
      exit 2
    }
    config_path="$workspace_parent/config.json"

    chown "$owner_user:$manager_group" "$owner_home"
    chmod u=rwx,g=rx,o= "$owner_home"
    if [[ "$workspace_parent" != "$owner_home" ]]; then
      chown "$owner_user:$manager_group" "$workspace_parent"
      chmod u=rwx,g=rx,o= "$workspace_parent"
    fi
    chown -R "$owner_user:$manager_group" "$workspace_root"
    chmod -R u=rwX,g=rwX,o= "$workspace_root"
    find "$workspace_root" -type d -exec chmod g+s {} +
    if [[ -f "$config_path" ]]; then
      chown "$owner_user:$manager_group" "$config_path"
      chmod u=rw,g=r,o= "$config_path"
    fi
    ;;

  grant_passwordless_sudo)
    username="${1:-}"
    require_existing_user "$username"
    sudoers_file="/etc/sudoers.d/omniclaw-${username}-nopasswd"
    tmp_file="$(mktemp)"
    trap 'rm -f "$tmp_file"' EXIT
    printf '%s ALL=(ALL:ALL) NOPASSWD: ALL\n' "$username" > "$tmp_file"
    chown root:root "$tmp_file"
    chmod 0440 "$tmp_file"
    visudo -cf "$tmp_file"
    install -o root -g root -m 0440 "$tmp_file" "$sudoers_file"
    visudo -cf "$sudoers_file"
    rm -f "$tmp_file"
    trap - EXIT
    echo "Granted passwordless sudo via $sudoers_file"
    ;;

  verify_passwordless_sudo)
    username="${1:-}"
    require_existing_user "$username"
    su -s /bin/bash -c 'sudo -n id -u' "$username"
    ;;

  *)
    usage
    exit 1
    ;;
esac
