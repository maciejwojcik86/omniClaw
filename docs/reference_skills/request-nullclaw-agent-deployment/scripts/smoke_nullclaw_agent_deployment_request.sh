#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
exec "$ROOT/scripts/forms/smoke_nullclaw_agent_deployment_request.sh" "$@"
