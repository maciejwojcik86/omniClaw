#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  start_local_stack.sh

Runs the OmniClaw kernel in the foreground. When `LITELLM_PROXY_URL` points to
`localhost` or `127.0.0.1`, `main.py` will auto-start the local LiteLLM proxy
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

export PYTHONPATH="/home/macos/nanobot:${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

exec uv run python main.py
