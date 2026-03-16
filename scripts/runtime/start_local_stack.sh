#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  start_local_stack.sh [--company <slug-or-display-name>] [--global-config-path <path>]
                       [--company-workspace-root <path>] [--company-config-path <path>]
                       [--database-url <url>] [uvicorn args...]

Runs the OmniClaw kernel in the foreground. When `LITELLM_PROXY_URL` points to
`localhost` or `127.0.0.1`, `omniclaw` will auto-start the local LiteLLM proxy
and stop it again on exit.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

company="${OMNICLAW_COMPANY:-}"
global_config_path="${OMNICLAW_GLOBAL_CONFIG_PATH:-}"
company_workspace_root="${OMNICLAW_COMPANY_WORKSPACE_ROOT:-}"
company_config_path="${OMNICLAW_COMPANY_CONFIG_PATH:-}"
database_url="${OMNICLAW_DATABASE_URL:-}"
forward_args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
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
    --company-config-path)
      company_config_path="$2"
      shift 2
      ;;
    --database-url)
      database_url="$2"
      shift 2
      ;;
    *)
      forward_args+=("$1")
      shift
      ;;
  esac
done

cmd=(uv run --project "$ROOT_DIR" omniclaw)
if [[ -n "$company" ]]; then
  cmd+=(--company "$company")
fi
if [[ -n "$global_config_path" ]]; then
  cmd+=(--global-config-path "$global_config_path")
fi
if [[ -n "$company_workspace_root" ]]; then
  cmd+=(--company-workspace-root "$company_workspace_root")
fi
if [[ -n "$company_config_path" ]]; then
  cmd+=(--company-config-path "$company_config_path")
fi
if [[ -n "$database_url" ]]; then
  cmd+=(--database-url "$database_url")
fi
cmd+=("${forward_args[@]}")

exec "${cmd[@]}"
