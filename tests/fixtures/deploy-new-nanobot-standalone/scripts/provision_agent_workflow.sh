#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "NOTE: provision_agent_workflow.sh is deprecated. Forwarding to deploy_new_nanobot.sh."

forward_args=("$@")

has_node_name=0
for arg in "$@"; do
  if [[ "$arg" == "--node-name" ]]; then
    has_node_name=1
    break
  fi
done

if [[ "$has_node_name" -eq 0 ]]; then
  username=""
  for ((idx=1; idx<=$#; idx++)); do
    if [[ "${!idx}" == "--username" ]]; then
      next=$((idx + 1))
      username="${!next:-}"
      break
    fi
  done
  if [[ -n "$username" ]]; then
    forward_args+=(--node-name "$username")
  fi
fi

exec "$SCRIPT_DIR/deploy_new_nanobot.sh" "${forward_args[@]}"
