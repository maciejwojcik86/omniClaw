#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  smoke_deploy_new_agent_e2e.sh [--apply] [--kernel-url <url>] [--database <sqlite-db>]
                                [--workflow-file <path>] [--initiator-workspace <path>]
                                [--request-file <name.md>] [--nanobot-bin <bin>]
                                [--scan-limit <n>] [--skip-agent-runs]
                                [--company <slug-or-display-name>] [--global-config-path <path>]
                                [--company-workspace-root <path>]
                                [--allow-agent-fallback]

Default mode is dry-run. Use --apply to execute.

Smoke objective:
1) Preflight participant/workflow readiness.
2) Seed deploy_new_agent request in initiator outbox.
3) Route through BUSINESS_CASE -> HR_REVIEW -> FINANCE_REVIEW ->
   DIRECTOR_APPROVAL -> AGENT_DEPLOYMENT -> ARCHIVED.
4) Wake holders one-by-one with heartbeat-only prompts.
5) Verify routed stage_skill metadata and final archive evidence.

If a holder is HUMAN (not AGENT), the script auto-prepares the decision file
for that stage to keep the smoke moving.
USAGE
}

dry_run=1
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
company="${OMNICLAW_COMPANY:-}"
global_config_path="${OMNICLAW_GLOBAL_CONFIG_PATH:-}"
company_workspace_root="${OMNICLAW_COMPANY_WORKSPACE_ROOT:-}"
database=""
workflow_file=""
initiator_workspace=""
request_file=""
nanobot_bin="nanobot"
scan_limit="200"
skip_agent_runs=0
allow_agent_fallback=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      dry_run=0
      shift
      ;;
    --kernel-url)
      kernel_url="$2"
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
    --database)
      database="$2"
      shift 2
      ;;
    --workflow-file)
      workflow_file="$2"
      shift 2
      ;;
    --initiator-workspace)
      initiator_workspace="$2"
      shift 2
      ;;
    --request-file)
      request_file="$2"
      shift 2
      ;;
    --nanobot-bin)
      nanobot_bin="$2"
      shift 2
      ;;
    --scan-limit)
      scan_limit="$2"
      shift 2
      ;;
    --company-workspace-root)
      company_workspace_root="$2"
      shift 2
      ;;
    --skip-agent-runs)
      skip_agent_runs=1
      shift
      ;;
    --allow-agent-fallback)
      allow_agent_fallback=1
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

if [[ -z "$request_file" ]]; then
  request_file="$(date +%Y-%m-%d)-m07-deploy-new-agent-e2e-smoke.md"
fi

if ! [[ "$scan_limit" =~ ^[0-9]+$ ]]; then
  echo "--scan-limit must be an integer" >&2
  exit 1
fi

if [[ -z "$company_workspace_root" ]]; then
  context_cmd=(uv run --project "$ROOT" python "$ROOT/scripts/company/show_company_context.py")
  if [[ -n "$company" ]]; then
    context_cmd+=(--company "$company")
  fi
  if [[ -n "$global_config_path" ]]; then
    context_cmd+=(--global-config-path "$global_config_path")
  fi
  context_cmd+=(--field workspace_root)
  company_workspace_root="$("${context_cmd[@]}")"
fi

if [[ -z "$database" ]]; then
  database="$company_workspace_root/omniclaw.db"
fi
if [[ -z "$workflow_file" ]]; then
  workflow_file="$company_workspace_root/forms/deploy_new_agent/workflow.json"
fi
if [[ -z "$initiator_workspace" ]]; then
  initiator_workspace="$company_workspace_root/macos"
fi

declare -A STAGE_DECISIONS=(
  ["BUSINESS_CASE"]="submit_to_hr"
  ["HR_REVIEW"]="approve_to_finance"
  ["FINANCE_REVIEW"]="approve_to_director"
  ["DIRECTOR_APPROVAL"]="execute_deployment"
  ["AGENT_DEPLOYMENT"]="deploy_and_archive"
)

STAGE_PATH=("BUSINESS_CASE" "HR_REVIEW" "FINANCE_REVIEW" "DIRECTOR_APPROVAL" "AGENT_DEPLOYMENT" "ARCHIVED")

declare -A NODE_TYPE_BY_NAME=()
declare -A NODE_USER_BY_NAME=()
declare -A NODE_WORKSPACE_BY_NAME=()
declare -A NODE_CONFIG_BY_NAME=()

log_step() {
  echo
  echo "[$1] $2"
}

run_or_print() {
  if [[ "$dry_run" -eq 1 ]]; then
    printf 'DRY-RUN: '
    printf '%q ' "$@"
    echo
    return 0
  fi
  "$@"
}

workflow_query() {
  local stage="$1"
  local kind="$2"
  local decision="${3:-}"
  uv run python - "$workflow_file" "$stage" "$kind" "$decision" <<'PY'
import json
import sys
from pathlib import Path

workflow_path = Path(sys.argv[1])
stage = sys.argv[2]
kind = sys.argv[3]
decision = sys.argv[4]

payload = json.loads(workflow_path.read_text(encoding="utf-8"))
stages = payload.get("stages")
if not isinstance(stages, dict):
    raise SystemExit("workflow.json missing 'stages' object")
if stage not in stages:
    raise SystemExit(f"stage '{stage}' missing from workflow")

node = stages[stage]
if not isinstance(node, dict):
    raise SystemExit(f"stage '{stage}' payload must be object")

if kind == "required_skill":
    value = node.get("required_skill")
    print("" if value is None else str(value))
elif kind == "target":
    value = node.get("target")
    if value is None:
        print("")
    else:
        print(str(value))
elif kind == "next_stage":
    decisions = node.get("decisions")
    if not isinstance(decisions, dict):
        raise SystemExit(f"stage '{stage}' missing decisions object")
    value = decisions.get(decision)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"stage '{stage}' missing decision '{decision}'")
    print(value.strip())
else:
    raise SystemExit(f"unknown query kind: {kind}")
PY
}

load_node() {
  local node_name="$1"
  if [[ -n "${NODE_TYPE_BY_NAME[$node_name]:-}" ]]; then
    return 0
  fi

  local row
  if ! row="$(uv run python - "$database" "$node_name" <<'PY'
import sqlite3
import sys
from pathlib import Path

db_path = Path(sys.argv[1])
node_name = sys.argv[2]
if not db_path.exists():
    raise SystemExit(f"database not found: {db_path}")

conn = sqlite3.connect(db_path)
cur = conn.cursor()
row = cur.execute(
    "SELECT type, COALESCE(linux_username, ''), COALESCE(workspace_root, ''), COALESCE(runtime_config_path, '') "
    "FROM nodes WHERE name = ? LIMIT 1",
    (node_name,),
).fetchone()
conn.close()

if row is None:
    raise SystemExit(2)

print(f"{row[0]}\t{row[1]}\t{row[2]}\t{row[3]}")
PY
)"; then
    echo "Node lookup failed for '$node_name' in '$database'" >&2
    exit 1
  fi

  local node_type=""
  local node_user=""
  local node_workspace=""
  local node_config=""
  IFS=$'\t' read -r node_type node_user node_workspace node_config <<<"$row"
  NODE_TYPE_BY_NAME["$node_name"]="$node_type"
  NODE_USER_BY_NAME["$node_name"]="$node_user"
  NODE_WORKSPACE_BY_NAME["$node_name"]="$node_workspace"
  NODE_CONFIG_BY_NAME["$node_name"]="$node_config"
}

frontmatter_value() {
  local markdown_file="$1"
  local key="$2"
  uv run python - "$markdown_file" "$key" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
text = path.read_text(encoding="utf-8")
if not text.startswith("---\n"):
    raise SystemExit("missing opening frontmatter delimiter")
lines = text.splitlines()
closing = None
for idx in range(1, len(lines)):
    if lines[idx].strip() == "---":
        closing = idx
        break
if closing is None:
    raise SystemExit("missing closing frontmatter delimiter")
for line in lines[1:closing]:
    raw = line.strip()
    if ":" not in raw:
        continue
    k, v = raw.split(":", 1)
    if k.strip() == key:
        print(v.strip().strip('"').strip("'"))
        raise SystemExit(0)
print("")
PY
}

assert_frontmatter_equals() {
  local markdown_file="$1"
  local key="$2"
  local expected="$3"
  local actual
  actual="$(frontmatter_value "$markdown_file" "$key")"
  if [[ "$actual" != "$expected" ]]; then
    echo "Frontmatter assertion failed for '$markdown_file': '$key' expected '$expected' got '$actual'" >&2
    exit 1
  fi
}

prepare_pending_decision_copy() {
  local holder_workspace="$1"
  local decision="$2"
  local stale_marker="$3"
  local source="$holder_workspace/inbox/new/$request_file"
  local target="$holder_workspace/outbox/send/$request_file"

  if [[ "$dry_run" -eq 1 ]]; then
    echo "DRY-RUN: prepare pending decision '$decision' from $source -> $target"
    return 0
  fi

  if [[ ! -f "$source" ]]; then
    echo "Cannot prepare pending decision: missing source '$source'" >&2
    exit 1
  fi

  uv run python - "$source" "$target" "$decision" "$stale_marker" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
target = Path(sys.argv[2])
decision = sys.argv[3]
stale_marker = sys.argv[4]

text = source.read_text(encoding="utf-8")
if not text.startswith("---\n"):
    raise SystemExit("source file missing frontmatter")
lines = text.splitlines()
closing = None
for idx in range(1, len(lines)):
    if lines[idx].strip() == "---":
        closing = idx
        break
if closing is None:
    raise SystemExit("source file missing frontmatter closing delimiter")

frontmatter: dict[str, str] = {}
for line in lines[1:closing]:
    raw = line.strip()
    if not raw or ":" not in raw:
        continue
    key, value = raw.split(":", 1)
    frontmatter[key.strip()] = value.strip().strip('"').strip("'")
frontmatter["decision"] = decision
frontmatter["stage_skill"] = stale_marker

body = "\n".join(lines[closing + 1 :]).rstrip("\n")
rendered = ["---"]
for key, value in frontmatter.items():
    rendered.append(f"{key}: {value}")
rendered.append("---")
rendered.append("")
if body:
    rendered.append(body)
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text("\n".join(rendered).rstrip("\n") + "\n", encoding="utf-8")
PY
}

run_holder_heartbeat() {
  local holder_name="$1"
  local holder_workspace="$2"
  local holder_config="$3"

  local prompt="Read HEARTBEAT.md in this workspace root and execute exactly one heartbeat cycle now."
  local shell_cmd=""
  printf -v shell_cmd 'cd %q && %q agent -w %q -c %q -m %q' \
    "$holder_workspace" \
    "$nanobot_bin" \
    "$holder_workspace" \
    "$holder_config" \
    "$prompt"
  run_or_print bash -lc "$shell_cmd"
}

scan_forms_once() {
  if [[ "$dry_run" -eq 1 ]]; then
    run_or_print "$ROOT/scripts/ipc/trigger_ipc_action.sh" \
      --kernel-url "$kernel_url" \
      --action scan_forms \
      --limit "$scan_limit"
    return 0
  fi
  "$ROOT/scripts/ipc/trigger_ipc_action.sh" \
    --apply \
    --kernel-url "$kernel_url" \
    --action scan_forms \
    --limit "$scan_limit"
  echo
}

log_step "1/8" "Preflight workflow and environment checks"
if [[ ! -f "$workflow_file" ]]; then
  echo "workflow file not found: $workflow_file" >&2
  exit 1
fi
if [[ ! -f "$database" ]]; then
  echo "database not found: $database" >&2
  exit 1
fi
if [[ ! -d "$initiator_workspace" ]]; then
  echo "initiator workspace not found: $initiator_workspace" >&2
  exit 1
fi

run_or_print uv --version
run_or_print "$ROOT/scripts/ipc/trigger_ipc_action.sh" --kernel-url "$kernel_url" --action scan_forms --limit "$scan_limit"

for ((idx = 0; idx < ${#STAGE_PATH[@]} - 1; idx++)); do
  stage="${STAGE_PATH[$idx]}"
  next_stage="${STAGE_PATH[$((idx + 1))]}"
  decision="${STAGE_DECISIONS[$stage]}"
  actual_next="$(workflow_query "$stage" "next_stage" "$decision")"
  if [[ "$actual_next" != "$next_stage" ]]; then
    echo "Workflow mismatch: '$stage' decision '$decision' -> '$actual_next' (expected '$next_stage')" >&2
    exit 1
  fi
done

for stage in HR_REVIEW FINANCE_REVIEW DIRECTOR_APPROVAL AGENT_DEPLOYMENT; do
  required_skill="$(workflow_query "$stage" "required_skill")"
  if [[ -z "$required_skill" ]]; then
    echo "Stage '$stage' requires a non-empty required_skill" >&2
    exit 1
  fi
  skill_file="$company_workspace_root/forms/deploy_new_agent/skills/$required_skill/SKILL.md"
  if [[ ! -f "$skill_file" ]]; then
    echo "Missing master stage skill: $skill_file" >&2
    exit 1
  fi
done

for agent_name in Director_01 HR_Head_01 Ops_Head_01; do
  load_node "$agent_name"
  agent_workspace="${NODE_WORKSPACE_BY_NAME[$agent_name]}"
  agent_config="${NODE_CONFIG_BY_NAME[$agent_name]}"
  if [[ -z "$agent_workspace" || ! -d "$agent_workspace" ]]; then
    echo "Node '$agent_name' has invalid workspace_root: '$agent_workspace'" >&2
    exit 1
  fi
  if [[ -z "$agent_config" || ! -f "$agent_config" ]]; then
    echo "Node '$agent_name' has invalid runtime_config_path: '$agent_config'" >&2
    exit 1
  fi
  if [[ ! -f "$agent_workspace/AGENTS.md" ]]; then
    echo "Node '$agent_name' missing AGENTS.md at '$agent_workspace/AGENTS.md'" >&2
    exit 1
  fi
  if [[ ! -f "$agent_workspace/HEARTBEAT.md" ]]; then
    echo "Node '$agent_name' missing HEARTBEAT.md at '$agent_workspace/HEARTBEAT.md'" >&2
    exit 1
  fi
done

log_step "2/8" "Seed deploy_new_agent request in initiator outbox queue"
request_path="$initiator_workspace/outbox/send/$request_file"
if [[ -e "$request_path" ]]; then
  echo "Request file already exists: $request_path" >&2
  exit 1
fi

first_target="$(workflow_query "HR_REVIEW" "target")"
if [[ -z "$first_target" || "$first_target" == "none" ]]; then
  echo "Workflow target for HR_REVIEW is empty; cannot seed initial target" >&2
  exit 1
fi

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN: write request file -> $request_path"
else
  mkdir -p "$(dirname "$request_path")"
  cat > "$request_path" <<EOF
---
form_type: deploy_new_agent
stage: BUSINESS_CASE
decision: submit_to_hr
target: $first_target
subject: M07 deploy_new_agent e2e smoke
---

## Smoke Request
- Requested role: QA_Agent_M07_Smoke
- Purpose: Validate full deploy_new_agent workflow routing and stage-skill handoff.
- Scope: E2E smoke for HR/Finance/Director/Deployment cycle.
EOF
fi

current_stage="BUSINESS_CASE"
for ((idx = 0; idx < ${#STAGE_PATH[@]} - 1; idx++)); do
  next_stage="${STAGE_PATH[$((idx + 1))]}"
  decision="${STAGE_DECISIONS[$current_stage]}"

  log_step "3/8" "Route transition $current_stage --($decision)--> $next_stage"
  scan_forms_once

  if [[ "$next_stage" == "ARCHIVED" ]]; then
    final_sender_workspace="$initiator_workspace"
    final_sender_name="$(workflow_query "$current_stage" "target")"
    if [[ -n "$final_sender_name" && "$final_sender_name" != "none" ]]; then
      load_node "$final_sender_name"
      final_sender_workspace="${NODE_WORKSPACE_BY_NAME[$final_sender_name]}"
    fi
    archive_copy="$final_sender_workspace/outbox/archive/$request_file"
    backup_glob="$company_workspace_root/form_archive/deploy_new_agent"
    if [[ "$dry_run" -eq 0 ]]; then
      if [[ ! -f "$archive_copy" ]]; then
        echo "Expected archive copy missing: $archive_copy" >&2
        exit 1
      fi
      assert_frontmatter_equals "$archive_copy" "stage" "ARCHIVED"
      assert_frontmatter_equals "$archive_copy" "stage_skill" ""
      if ! find "$backup_glob" -type f -name "*$request_file" -print -quit | grep -q .; then
        echo "No backup archive copy found for '$request_file' under '$backup_glob'" >&2
        exit 1
      fi
    else
      echo "DRY-RUN: expect final archive copy at $archive_copy"
      echo "DRY-RUN: expect backup copy under $backup_glob"
    fi
    break
  fi

  holder_name="$(workflow_query "$next_stage" "target")"
  if [[ -z "$holder_name" || "$holder_name" == "none" ]]; then
    echo "Expected non-terminal holder for stage '$next_stage', got '$holder_name'" >&2
    exit 1
  fi
  load_node "$holder_name"
  holder_type="${NODE_TYPE_BY_NAME[$holder_name]}"
  holder_workspace="${NODE_WORKSPACE_BY_NAME[$holder_name]}"
  holder_config="${NODE_CONFIG_BY_NAME[$holder_name]}"

  if [[ -z "$holder_workspace" || ! -d "$holder_workspace" ]]; then
    echo "Holder '$holder_name' has invalid workspace_root '$holder_workspace'" >&2
    exit 1
  fi

  delivered_path="$holder_workspace/inbox/new/$request_file"
  expected_stage_skill="$(workflow_query "$next_stage" "required_skill")"
  expected_skill_copy="$holder_workspace/skills/$expected_stage_skill/SKILL.md"

  if [[ "$dry_run" -eq 0 ]]; then
    if [[ ! -f "$delivered_path" ]]; then
      echo "Expected delivered form missing: $delivered_path" >&2
      exit 1
    fi
    assert_frontmatter_equals "$delivered_path" "stage" "$next_stage"
    assert_frontmatter_equals "$delivered_path" "stage_skill" "$expected_stage_skill"
    if [[ ! -f "$expected_skill_copy" ]]; then
      echo "Expected distributed stage skill missing: $expected_skill_copy" >&2
      exit 1
    fi
  else
    echo "DRY-RUN: expect delivery at $delivered_path"
    echo "DRY-RUN: expect stage skill copy at $expected_skill_copy"
  fi

  holder_decision="${STAGE_DECISIONS[$next_stage]:-}"
  if [[ -z "$holder_decision" ]]; then
    current_stage="$next_stage"
    continue
  fi

  log_step "4/8" "Prepare holder action for stage $next_stage (decision: $holder_decision)"
  if [[ "$skip_agent_runs" -eq 0 && "$holder_type" == "AGENT" && -n "$holder_config" ]]; then
    run_holder_heartbeat "$holder_name" "$holder_workspace" "$holder_config"
    pending_path="$holder_workspace/outbox/send/$request_file"
    if [[ "$dry_run" -eq 0 && ! -f "$pending_path" ]]; then
      if [[ "$allow_agent_fallback" -eq 1 ]]; then
        echo "Agent '$holder_name' did not produce pending decision file; applying fallback copy."
        prepare_pending_decision_copy "$holder_workspace" "$holder_decision" "stale-fallback-$next_stage"
      else
        echo "Agent '$holder_name' did not produce '$pending_path'." >&2
        echo "Run again with --allow-agent-fallback to auto-seed this stage if needed." >&2
        exit 1
      fi
    fi
  else
    echo "Holder '$holder_name' is not running as AGENT in this smoke path; preparing decision file directly."
    prepare_pending_decision_copy "$holder_workspace" "$holder_decision" "stale-human-$next_stage"
  fi

  current_stage="$next_stage"
done

log_step "5/8" "Smoke sequence complete"
echo "Request file: $request_file"
echo "Kernel URL:   $kernel_url"
echo "Mode:         $([[ "$dry_run" -eq 1 ]] && echo 'dry-run' || echo 'apply')"
