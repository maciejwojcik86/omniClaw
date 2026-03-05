#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${1:-workspace/omniclaw.db}"

python3 - <<'PY' "$DB_PATH"
import sqlite3
import sys

path = sys.argv[1]
conn = sqlite3.connect(path)
cur = conn.cursor()
cur.execute("SELECT version_num FROM alembic_version")
row = cur.fetchone()
print(f"revision={row[0] if row else '<missing>'}")

cur.execute("PRAGMA table_info(nodes)")
cols = [r[1] for r in cur.fetchall()]
required = {
    "linux_username",
    "linux_password",
    "workspace_root",
    "nullclaw_config_path",
    "primary_model",
    "gateway_running",
    "gateway_pid",
    "gateway_host",
    "gateway_port",
    "gateway_started_at",
    "gateway_stopped_at",
}
missing = sorted(required - set(cols))
print("node_columns=", ",".join(cols))
if missing:
    print("missing_columns=", ",".join(missing))
    raise SystemExit(1)
print("status=ok")

cur.execute("PRAGMA index_list(hierarchy)")
indexes = cur.fetchall()
single_manager_index = False
index_names = []
for row in indexes:
    # (seq, name, unique, origin, partial)
    idx_name = row[1]
    is_unique = bool(row[2])
    index_names.append(idx_name)
    if not is_unique:
        continue
    cur.execute(f"PRAGMA index_info('{idx_name}')")
    idx_cols = [c[2] for c in cur.fetchall()]
    if idx_cols == ["child_node_id"]:
        single_manager_index = True
print("hierarchy_indexes=", ",".join(sorted(index_names)))
if not single_manager_index:
    print("missing_unique_child_manager_index=true")
    raise SystemExit(1)

conn.close()
PY
