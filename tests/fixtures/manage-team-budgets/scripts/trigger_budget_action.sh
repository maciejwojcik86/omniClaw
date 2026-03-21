#!/usr/bin/env bash
set -euo pipefail

find_repo_root() {
  local start_dir search_dir
  start_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  search_dir="$start_dir"
  while true; do
    if [[ -f "$search_dir/pyproject.toml" && -d "$search_dir/workspace" ]]; then
      printf '%s\n' "$search_dir"
      return 0
    fi
    if [[ "$search_dir" == "/" ]]; then
      break
    fi
    search_dir="$(dirname "$search_dir")"
  done
  return 1
}

REPO_ROOT="$(find_repo_root)" || {
  echo "Unable to locate OmniClaw repo root for budget action helper" >&2
  exit 1
}

exec bash "$REPO_ROOT/scripts/budgets/trigger_budget_action.sh" "$@"
