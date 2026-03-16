#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  upsert_workflow_from_workspace.sh [--apply] [--activate]
                                  [--form-type <type_key>]
                                  [--workflow-file <path>]
                                  [--company <slug-or-display-name>] [--global-config-path <path>]
                                  [--company-workspace-root <path>]
                                  [--version <ver>]
                                  [--kernel-url <url>]

Reads workspace workflow JSON and submits forms action upsert_form_type.
Dry-run by default.
USAGE
}

dry_run=1
activate=0
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
company="${OMNICLAW_COMPANY:-}"
global_config_path="${OMNICLAW_GLOBAL_CONFIG_PATH:-}"
company_workspace_root="${OMNICLAW_COMPANY_WORKSPACE_ROOT:-}"
form_type=""
workflow_file=""
version_override=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      dry_run=0
      shift
      ;;
    --activate)
      activate=1
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
    --form-type)
      form_type="$2"
      shift 2
      ;;
    --workflow-file)
      workflow_file="$2"
      shift 2
      ;;
    --company-workspace-root)
      company_workspace_root="$2"
      shift 2
      ;;
    --version)
      version_override="$2"
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

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 1
fi

if [[ -z "$form_type" && -z "$workflow_file" ]]; then
  echo "Provide --form-type or --workflow-file" >&2
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

if [[ -n "$form_type" && -z "$workflow_file" ]]; then
  workflow_file="${company_workspace_root}/forms/${form_type}/workflow.json"
fi

if [[ ! -f "$workflow_file" ]]; then
  echo "workflow file not found: $workflow_file" >&2
  exit 1
fi

if [[ -z "$form_type" ]]; then
  form_type="$(jq -r '.form_type // empty' "$workflow_file")"
fi
if [[ -z "$form_type" ]]; then
  echo "form_type is missing in workflow file" >&2
  exit 1
fi

version="${version_override}"
if [[ -z "$version" ]]; then
  version="$(jq -r '.version // empty' "$workflow_file")"
fi
if [[ -z "$version" ]]; then
  version="1.0.0"
fi

description="$(jq -r '.description // empty' "$workflow_file")"

payload_file="$(mktemp)"
trap 'rm -f "$payload_file"' EXIT

jq -n \
  --arg action "upsert_form_type" \
  --arg type_key "$form_type" \
  --arg version "$version" \
  --arg description "$description" \
  --slurpfile workflow "$workflow_file" \
  '{
    action: $action,
    type_key: $type_key,
    version: $version,
    description: ($description | select(length > 0)),
    workflow_graph: $workflow[0],
    stage_metadata: {}
  }' > "$payload_file"

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN workflow publish for '$form_type' version '$version'"
  cat "$payload_file"
  exit 0
fi

"$ROOT/scripts/forms/trigger_forms_action.sh" \
  --apply \
  --kernel-url "$kernel_url" \
  --body-file "$payload_file"

if [[ "$activate" -eq 1 ]]; then
  "$ROOT/scripts/forms/trigger_forms_action.sh" \
    --apply \
    --kernel-url "$kernel_url" \
    --action validate_form_type \
    --type-key "$form_type" \
    --version "$version"

  "$ROOT/scripts/forms/trigger_forms_action.sh" \
    --apply \
    --kernel-url "$kernel_url" \
    --action activate_form_type \
    --type-key "$form_type" \
    --version "$version"
fi
