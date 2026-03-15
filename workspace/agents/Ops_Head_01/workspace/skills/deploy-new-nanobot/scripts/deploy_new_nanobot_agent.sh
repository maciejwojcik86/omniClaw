#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "NOTE: deploy_new_nanobot_agent.sh is deprecated. Forwarding to deploy_new_nanobot.sh."
exec "$SCRIPT_DIR/deploy_new_nanobot.sh" "$@"
