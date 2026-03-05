#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
OUT="$ROOT/.codex/skills/nullclaw-runtime-reference/references/cache"
REPO_DIR="$OUT/nullclaw-repo"
SITE_DIR="$OUT/nullclaw-site"

mkdir -p "$OUT" "$SITE_DIR"

if [[ -d "$REPO_DIR/.git" ]]; then
  git -C "$REPO_DIR" fetch --depth 1 origin main
  git -C "$REPO_DIR" checkout main
  git -C "$REPO_DIR" pull --ff-only origin main
else
  git clone --depth 1 https://github.com/nullclaw/nullclaw.git "$REPO_DIR"
fi

cp "$REPO_DIR/README.md" "$OUT/README.md"
cp "$REPO_DIR/config.example.json" "$OUT/config.example.json"
cp "$REPO_DIR/spec/webchannel_v1.json" "$OUT/webchannel_v1.json"
cp "$REPO_DIR/examples/meshrelay/README.md" "$OUT/meshrelay-README.md"
cp "$REPO_DIR/examples/modal-matrix/README.md" "$OUT/modal-matrix-README.md"
cp "$REPO_DIR/examples/modal-matrix/config.matrix.example.json" "$OUT/config.matrix.example.json"

pages=(
  ""
  "getting-started.html"
  "configuration.html"
  "providers.html"
  "channels.html"
  "tools.html"
  "cli.html"
  "architecture.html"
  "deployment/network.html"
  "security/overview.html"
  "security/sandboxing.html"
  "security/resource-limits.html"
  "security/audit-logging.html"
  "security/roadmap.html"
)

for p in "${pages[@]}"; do
  if [[ -z "$p" ]]; then
    curl -sL "https://nullclaw.github.io/" > "$SITE_DIR/index.html"
  else
    out_name="${p//\//-}"
    curl -sL "https://nullclaw.github.io/$p" > "$SITE_DIR/$out_name"
  fi
done

echo "Snapshot updated in: $OUT"
