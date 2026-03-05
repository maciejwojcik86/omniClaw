#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  install_shared_nullclaw_binary.sh [--apply] [--binary-path <path-or-command>] [--install-root <path>] [--version <version>] [--target-name <name>]

Default mode is dry-run. Use --apply to execute.
USAGE
}

dry_run=1
binary_path="nullclaw"
install_root="/opt/omniclaw"
version=""
target_name="nullclaw"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      dry_run=0
      shift
      ;;
    --binary-path)
      binary_path="$2"
      shift 2
      ;;
    --install-root)
      install_root="$2"
      shift 2
      ;;
    --version)
      version="$2"
      shift 2
      ;;
    --target-name)
      target_name="$2"
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

resolved_bin=""
if [[ -x "$binary_path" ]]; then
  resolved_bin="$binary_path"
elif command -v "$binary_path" >/dev/null 2>&1; then
  resolved_bin="$(command -v "$binary_path")"
fi

if [[ -z "$resolved_bin" ]]; then
  echo "Could not resolve nullclaw binary from '$binary_path'" >&2
  echo "Hint: build nullclaw first or pass --binary-path /abs/path/to/nullclaw" >&2
  exit 1
fi

if [[ -z "$version" ]]; then
  detected="$("$resolved_bin" --version 2>/dev/null || true)"
  # Expected format: "nullclaw 2026.2.26"
  version="$(awk '{print $2}' <<<"$detected" | tr -d '[:space:]')"
fi
if [[ -z "$version" ]]; then
  echo "Could not detect version from '$resolved_bin --version'; pass --version explicitly." >&2
  exit 1
fi

version_dir="$install_root/nullclaw/$version"
versioned_binary="$version_dir/$target_name"
shared_bin_dir="$install_root/bin"
shared_link="$shared_bin_dir/$target_name"

if [[ "$dry_run" -eq 1 ]]; then
  echo "DRY-RUN: install -d -m 0755 '$version_dir'"
  echo "DRY-RUN: install -D -m 0755 '$resolved_bin' '$versioned_binary'"
  echo "DRY-RUN: chown root:root '$versioned_binary'"
  echo "DRY-RUN: install -d -m 0755 '$shared_bin_dir'"
  echo "DRY-RUN: ln -sfn '$versioned_binary' '$shared_link'"
  echo "DRY-RUN: chown -h root:root '$shared_link'"
  exit 0
fi

install -d -m 0755 "$version_dir"
install -D -m 0755 "$resolved_bin" "$versioned_binary"
chown root:root "$versioned_binary"
install -d -m 0755 "$shared_bin_dir"
ln -sfn "$versioned_binary" "$shared_link"
chown -h root:root "$shared_link"

echo "Installed shared nullclaw binary: $versioned_binary"
echo "Updated shared link: $shared_link -> $versioned_binary"
