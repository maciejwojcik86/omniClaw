#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  trigger_forms_action.sh [--apply] [--kernel-url <url>] [--endpoint <path>] --action <action>
                          [--type-key <key>] [--version <ver>] [--form-id <id>]
                          [--body-file <json-file>]

Default mode is dry-run. Use --apply to execute HTTP POST.
Actions: upsert_form_type, validate_form_type, activate_form_type, deprecate_form_type,
         delete_form_type, list_form_types, create_form, transition_form, acknowledge_message_read
USAGE
}

dry_run=1
kernel_url="${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}"
endpoint="/v1/forms/actions"
action=""
type_key=""
version=""
form_id=""
body_file=""

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
    --endpoint)
      endpoint="$2"
      shift 2
      ;;
    --action)
      action="$2"
      shift 2
      ;;
    --type-key)
      type_key="$2"
      shift 2
      ;;
    --version)
      version="$2"
      shift 2
      ;;
    --form-id)
      form_id="$2"
      shift 2
      ;;
    --body-file)
      body_file="$2"
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

if [[ -z "$action" ]]; then
  echo "--action is required" >&2
  usage
  exit 1
fi

case "$action" in
  upsert_form_type|validate_form_type|activate_form_type|deprecate_form_type|delete_form_type|list_form_types|create_form|transition_form|acknowledge_message_read)
    ;;
  *)
    echo "Invalid --action '$action'" >&2
    usage
    exit 1
    ;;
esac

payload_file="$(mktemp)"
trap 'rm -f "$payload_file"' EXIT

if [[ -n "$body_file" ]]; then
  if [[ ! -f "$body_file" ]]; then
    echo "--body-file '$body_file' not found" >&2
    exit 1
  fi
  cat "$body_file" > "$payload_file"
else
  type_key_json="null"
  version_json="null"
  form_id_json="null"
  if [[ -n "$type_key" ]]; then
    type_key_json="\"$type_key\""
  fi
  if [[ -n "$version" ]]; then
    version_json="\"$version\""
  fi
  if [[ -n "$form_id" ]]; then
    form_id_json="\"$form_id\""
  fi

  cat > "$payload_file" <<JSON
{
  "action": "$action",
  "type_key": $type_key_json,
  "version": $version_json,
  "form_id": $form_id_json
}
JSON
fi

url="${kernel_url%/}${endpoint}"

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN forms request: POST $url"
  cat "$payload_file"
  exit 0
fi

curl --fail --show-error --silent \
  -X POST \
  -H 'Content-Type: application/json' \
  --data-binary "@$payload_file" \
  "$url"

echo
