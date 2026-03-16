#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

usage() {
  cat <<'USAGE'
Usage:
  bootstrap_monorepo.sh [--no-dev] [--refresh]

Creates or updates the shared monorepo virtualenv so both `omniclaw` and
`nanobot` are installed from this repository and available via `.venv/bin/`.
USAGE
}

sync_args=(sync)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-dev)
      sync_args+=(--no-dev)
      shift
      ;;
    --refresh)
      sync_args+=(--refresh)
      shift
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

echo "Syncing OmniClaw monorepo environment..."
uv "${sync_args[@]}"

echo
echo "Installed commands:"
echo "  $ROOT_DIR/.venv/bin/omniclaw --help"
echo "  $ROOT_DIR/.venv/bin/nanobot --help"
echo
echo "To use the commands directly in this shell:"
echo "  source \"$ROOT_DIR/.venv/bin/activate\""
