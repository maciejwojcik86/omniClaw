#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

find_repo_root() {
  local start_dir search_dir
  start_dir="${OMNICLAW_REPO_ROOT:-$SKILL_DIR}"
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
  REPO_ROOT=""
}

resolve_input_path() {
  local raw_path prefer_skill_dir candidate
  raw_path="$1"
  prefer_skill_dir="${2:-0}"
  if [[ -z "$raw_path" ]]; then
    return 0
  fi
  if [[ "$raw_path" = /* ]]; then
    python3 - "$raw_path" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
    return 0
  fi
  if [[ "$prefer_skill_dir" == "1" ]]; then
    candidate="$SKILL_DIR/$raw_path"
    if [[ -e "$candidate" ]]; then
      python3 - "$candidate" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
      return 0
    fi
  fi
  if [[ -e "$raw_path" ]]; then
    python3 - "$raw_path" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
    return 0
  fi
  if [[ "$prefer_skill_dir" != "1" ]]; then
    candidate="$SKILL_DIR/$raw_path"
    if [[ -e "$candidate" ]]; then
      python3 - "$candidate" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
      return 0
    fi
  fi
  printf '%s\n' "$raw_path"
}

usage() {
  cat <<'USAGE'
Usage:
  deploy_new_nanobot.sh [--apply] --node-name <node>
                        [--username <legacy-linux-username>]
                        [--manager-node-id <id> | --manager-node-name <name>]
                        [--manager-name <display-name>]
                        [--role-name <role>]
                        [--workspace-root <path>]
                        [--runtime-config-path <path>]
                        [--seed-config <path>]
                        [--primary-model <model>]
                        [--autonomy-level <int>]
                        [--linux-password <value>]
                        [--agents-source-file <path>]
                        [--company-workspace-root <path>]
                        [--kernel-url <url>]

Default mode is dry-run. Use --apply to execute the provisioning request, refresh config, and write AGENTS.md.
USAGE
}

dry_run=1
node_name=""
username=""
manager_node_id=""
manager_node_name=""
manager_name=""
role_name="Worker Agent"
workspace_root=""
runtime_config_path=""
seed_config="$SKILL_DIR/templates/nanobot_seed_config.json"
primary_model=""
autonomy_level="2"
linux_password=""
agents_source_file=""
company_workspace_root="${OMNICLAW_COMPANY_WORKSPACE_ROOT:-$HOME/.omniClaw/workspace}"
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      dry_run=0
      shift
      ;;
    --node-name)
      node_name="$2"
      shift 2
      ;;
    --username)
      username="$2"
      shift 2
      ;;
    --manager-node-id)
      manager_node_id="$2"
      shift 2
      ;;
    --manager-node-name)
      manager_node_name="$2"
      shift 2
      ;;
    --manager-name)
      manager_name="$2"
      shift 2
      ;;
    --role-name)
      role_name="$2"
      shift 2
      ;;
    --workspace-root)
      workspace_root="$2"
      shift 2
      ;;
    --runtime-config-path)
      runtime_config_path="$2"
      shift 2
      ;;
    --seed-config)
      seed_config="$2"
      shift 2
      ;;
    --primary-model)
      primary_model="$2"
      shift 2
      ;;
    --autonomy-level)
      autonomy_level="$2"
      shift 2
      ;;
    --linux-password)
      linux_password="$2"
      shift 2
      ;;
    --agents-source-file)
      agents_source_file="$2"
      shift 2
      ;;
    --company-workspace-root)
      company_workspace_root="$2"
      shift 2
      ;;
    --kernel-url)
      kernel_url="$2"
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

if [[ -z "$node_name" ]]; then
  echo "--node-name is required" >&2
  usage
  exit 1
fi

if [[ -z "$manager_node_id" && -z "$manager_node_name" ]]; then
  echo "--manager-node-id or --manager-node-name is required" >&2
  usage
  exit 1
fi

if [[ -z "$workspace_root" ]]; then
  workspace_root="$company_workspace_root/agents/$node_name/workspace"
fi

if [[ -z "$runtime_config_path" ]]; then
  runtime_config_path="$(
    python3 - "$workspace_root" <<'PY'
from pathlib import Path
import sys

workspace_root = Path(sys.argv[1]).expanduser().resolve()
print(workspace_root.parent / "config.json")
PY
  )"
fi

if [[ -z "$manager_name" ]]; then
  if [[ -n "$manager_node_name" ]]; then
    manager_name="$manager_node_name"
  else
    manager_name="Assigned Manager"
  fi
fi

if [[ -n "$seed_config" ]]; then
  seed_config="$(resolve_input_path "$seed_config" 1)"
fi

if [[ -n "$agents_source_file" ]]; then
  agents_source_file="$(resolve_input_path "$agents_source_file")"
fi

if [[ -n "$agents_source_file" && ! -f "$agents_source_file" ]]; then
  echo "AGENTS source file not found: $agents_source_file" >&2
  exit 1
fi

if [[ -n "$seed_config" && ! -f "$seed_config" ]]; then
  echo "Seed config not found: $seed_config" >&2
  exit 1
fi

payload_file="$(mktemp)"
trap 'rm -f "$payload_file"' EXIT

python3 - "$payload_file" "$node_name" "$username" "$manager_node_id" "$manager_node_name" "$workspace_root" "$runtime_config_path" "$primary_model" "$autonomy_level" "$linux_password" <<'PY'
import json
import sys

payload_path = sys.argv[1]
node_name = sys.argv[2]
username = sys.argv[3]
manager_node_id = sys.argv[4]
manager_node_name = sys.argv[5]
workspace_root = sys.argv[6]
runtime_config_path = sys.argv[7]
primary_model = sys.argv[8]
autonomy_level = int(sys.argv[9])
linux_password = sys.argv[10]

payload = {
    "action": "provision_agent",
    "node_name": node_name,
    "workspace_root": workspace_root,
    "runtime_config_path": runtime_config_path,
    "autonomy_level": autonomy_level,
}
if username:
    payload["username"] = username
if manager_node_id:
    payload["manager_node_id"] = manager_node_id
if manager_node_name:
    payload["manager_node_name"] = manager_node_name
if primary_model:
    payload["primary_model"] = primary_model
if linux_password:
    payload["linux_password"] = linux_password

with open(payload_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")
PY

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN provisioning payload:"
  cat "$payload_file"
  if [[ -n "$seed_config" ]]; then
    echo "DRY-RUN seed config: $seed_config"
  fi
  echo
  echo "DRY-RUN AGENTS write target: $workspace_root/AGENTS.md"
  exit 0
fi

"$SCRIPT_DIR/trigger_kernel_action.sh" \
  --apply \
  --kernel-url "$kernel_url" \
  --payload-file "$payload_file"

python3 "$SCRIPT_DIR/create_workspace_tree.py" \
  --apply \
  --workspace-root "$workspace_root"

init_cmd=(
  python3 "$SCRIPT_DIR/init_nanobot_config.py"
  --apply
  --workspace-root "$workspace_root"
  --config-path "$runtime_config_path"
)
if [[ -n "$seed_config" ]]; then
  init_cmd+=(--seed-config "$seed_config")
fi
if [[ -n "$primary_model" ]]; then
  init_cmd+=(--primary-model "$primary_model")
fi
"${init_cmd[@]}"

agents_cmd=(
  python3 "$SCRIPT_DIR/write_agent_instructions.py"
  --apply
  --workspace-root "$workspace_root"
  --node-name "$node_name"
  --manager-name "$manager_name"
  --role-name "$role_name"
)
if [[ -n "$primary_model" ]]; then
  agents_cmd+=(--primary-model "$primary_model")
fi
if [[ -n "$agents_source_file" ]]; then
  agents_cmd+=(--source-file "$agents_source_file")
fi
"${agents_cmd[@]}"

echo "Nanobot agent deployment complete."
echo "Workspace: $workspace_root"
echo "Config: $runtime_config_path"
echo "Manual smoke:"
echo "  nanobot agent -w \"$workspace_root\" -c \"$runtime_config_path\" -m \"Hello\""
echo "  nanobot gateway -w \"$workspace_root\" -c \"$runtime_config_path\" -p 18793"
