#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  requeue_dead_letter.sh --workspace-root <path> --file <dead-letter-file> [--apply]

Default mode is dry-run. Use --apply to move file from dead-letter to pending queue.
USAGE
}

dry_run=1
workspace_root=""
source_file=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      dry_run=0
      shift
      ;;
    --workspace-root)
      workspace_root="$2"
      shift 2
      ;;
    --file)
      source_file="$2"
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

if [[ -z "$workspace_root" || -z "$source_file" ]]; then
  usage
  exit 1
fi

workspace_root="$(realpath "$workspace_root")"
dead_letter_dir="$workspace_root/outbox/dead-letter"
pending_dir="$workspace_root/outbox/pending"

if [[ ! -d "$dead_letter_dir" ]]; then
  echo "dead-letter directory not found: $dead_letter_dir" >&2
  exit 1
fi

if [[ "$source_file" = /* ]]; then
  source_path="$(realpath "$source_file")"
else
  source_path="$(realpath "$dead_letter_dir/$source_file")"
fi

case "$source_path" in
  "$dead_letter_dir"/*) ;;
  *)
    echo "source file must be inside dead-letter directory: $dead_letter_dir" >&2
    exit 1
    ;;
esac

if [[ ! -f "$source_path" ]]; then
  echo "dead-letter file not found: $source_path" >&2
  exit 1
fi

mkdir -p "$pending_dir"

base_name="$(basename "$source_path")"
target_path="$pending_dir/$base_name"

if [[ -e "$target_path" ]]; then
  stem="${base_name%.*}"
  suffix=""
  if [[ "$base_name" == *.* ]]; then
    suffix=".${base_name##*.}"
  fi
  counter=1
  while [[ -e "$pending_dir/${stem}-${counter}${suffix}" ]]; do
    counter=$((counter + 1))
  done
  target_path="$pending_dir/${stem}-${counter}${suffix}"
fi

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN requeue"
  echo "source: $source_path"
  echo "target: $target_path"
  exit 0
fi

mv "$source_path" "$target_path"
echo "requeued: $target_path"
