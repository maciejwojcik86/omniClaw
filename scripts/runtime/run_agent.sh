#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run_agent.sh --agent-name <name> --message <text> [--session-key <key>]
               [--company <slug-or-display-name>] [--global-config-path <path>]
               [--company-workspace-root <path>]

Runs a Nanobot agent from the monorepo package environment and enables the
OmniClaw runtime integration hook for usage and prompt logging.
USAGE
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

agent_name=""
message=""
session_key=""
company="${OMNICLAW_COMPANY:-}"
global_config_path="${OMNICLAW_GLOBAL_CONFIG_PATH:-}"
company_workspace_root="${OMNICLAW_COMPANY_WORKSPACE_ROOT:-}"

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
    --company)
      company="$2"
      shift 2
      ;;
    --global-config-path)
      global_config_path="$2"
      shift 2
      ;;
    --company-workspace-root)
      company_workspace_root="$2"
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

if [[ -z "$company_workspace_root" ]]; then
  context_cmd=(uv run --project "$ROOT_DIR" python "$ROOT_DIR/scripts/company/show_company_context.py")
  if [[ -n "$company" ]]; then
    context_cmd+=(--company "$company")
  fi
  if [[ -n "$global_config_path" ]]; then
    context_cmd+=(--global-config-path "$global_config_path")
  fi
  context_cmd+=(--field workspace_root)
  company_workspace_root="$("${context_cmd[@]}")"
fi

workspace_root="${company_workspace_root}/agents/${agent_name}/workspace"
config_path="${company_workspace_root}/agents/${agent_name}/config.json"
database_url="${OMNICLAW_DATABASE_URL:-sqlite:///${company_workspace_root}/omniclaw.db}"
runtime_output_rel="${OMNICLAW_RUNTIME_OUTPUT_BOUNDARY_REL:-drafts/runtime}"
runtime_output_root="${workspace_root}/${runtime_output_rel}"

if [[ ! -d "$workspace_root" ]]; then
  echo "Missing workspace: $workspace_root" >&2
  exit 1
fi

if [[ ! -f "$config_path" ]]; then
  echo "Missing config: $config_path" >&2
  exit 1
fi

export OMNICLAW_RUNTIME_INTEGRATION_FACTORY="omniclaw.runtime_integration.hook:build_runtime_integration"
export OMNICLAW_RUNTIME_DATABASE_URL="$database_url"
export OMNICLAW_RUNTIME_NODE_NAME="$agent_name"
export OMNICLAW_RUNTIME_OUTPUT_ROOT="$runtime_output_root"
export OMNICLAW_RUNTIME_PROMPT_LOG_ROOT="$runtime_output_root/prompt_logs"
export OMNICLAW_RUNTIME_CALL_SOURCE="scripts/runtime/run_agent.sh"

cmd=(
  uv run --project "$ROOT_DIR" nanobot agent
  -w "$workspace_root"
  -c "$config_path"
  -m "$message"
)

if [[ -n "$session_key" ]]; then
  cmd+=(-s "$session_key")
fi

"${cmd[@]}"
