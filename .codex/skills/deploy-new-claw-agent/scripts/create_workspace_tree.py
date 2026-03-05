#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
exec uv run python "$ROOT/scripts/provisioning/create_workspace_tree.py" "$@"
