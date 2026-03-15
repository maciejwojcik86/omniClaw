#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run_agent.sh --agent-name <name> --message <text> [--session-key <key>]

Runs a repo-local Nanobot agent with the OmniClaw and Nanobot source trees on
PYTHONPATH so usage/cost logging can be persisted correctly.
USAGE
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

agent_name=""
message=""
session_key=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent-name)
      agent_name="$2"
      shift 2
      ;;
    --message|-m)
      message="$2"
      shift 2
      ;;
    --session-key|-s)
      session_key="$2"
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

if [[ -z "$agent_name" || -z "$message" ]]; then
  usage
  exit 1
fi

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

export PYTHONPATH="/home/macos/nanobot:${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

workspace_root="${ROOT_DIR}/workspace/agents/${agent_name}/workspace"
config_path="${ROOT_DIR}/workspace/agents/${agent_name}/config.json"

if [[ ! -d "$workspace_root" ]]; then
  echo "Missing workspace: $workspace_root" >&2
  exit 1
fi

if [[ ! -f "$config_path" ]]; then
  echo "Missing config: $config_path" >&2
  exit 1
fi

cmd=(
  uv run nanobot agent
  -w "$workspace_root"
  -c "$config_path"
  -m "$message"
)

if [[ -n "$session_key" ]]; then
  cmd+=(-s "$session_key")
fi

"${cmd[@]}"
