#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  package_nanobot_source.sh [--apply] [--source-dir <path>] [--output-dir <path>] [--archive-name <name>]
                            [--company <slug-or-display-name>] [--global-config-path <path>]
                            [--company-workspace-root <path>]

Default mode is dry-run. Use --apply to create the archive.
USAGE
}

dry_run=1
source_dir="$ROOT/third_party/nanobot"
company="${OMNICLAW_COMPANY:-}"
global_config_path="${OMNICLAW_GLOBAL_CONFIG_PATH:-}"
company_workspace_root="${OMNICLAW_COMPANY_WORKSPACE_ROOT:-}"
output_dir=""
archive_name=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      dry_run=0
      shift
      ;;
    --source-dir)
      source_dir="$2"
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
    --output-dir)
      output_dir="$2"
      shift 2
      ;;
    --company-workspace-root)
      company_workspace_root="$2"
      shift 2
      ;;
    --archive-name)
      archive_name="$2"
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

if [[ ! -d "$source_dir" ]]; then
  echo "Nanobot source directory not found: $source_dir" >&2
  exit 1
fi

if [[ -z "$output_dir" ]]; then
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
  output_dir="$company_workspace_root/runtime_packages"
fi

if [[ -z "$archive_name" ]]; then
  archive_name="nanobot-monorepo-$(date +%Y%m%d).tar.gz"
fi

archive_path="$output_dir/$archive_name"

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN package source: $source_dir"
  echo "DRY-RUN archive path: $archive_path"
  exit 0
fi

mkdir -p "$output_dir"
tar -czf "$archive_path" -C "$(dirname "$source_dir")" "$(basename "$source_dir")"
echo "Created Nanobot source archive: $archive_path"
