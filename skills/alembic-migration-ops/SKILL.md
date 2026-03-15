---
name: alembic-migration-ops
description: >
  How to create, run, verify, and troubleshoot OmniClaw database migrations with Alembic.
  Use when changing SQLAlchemy models, adding columns/tables, upgrading existing sqlite DBs,
  or validating migration success for runtime/provisioning features.
---

Use this skill when you need safe, repeatable schema migrations in OmniClaw.

## Installation

See [SETUP.md](./SETUP.md) for environment checks and one-time prerequisites.

## Scope

- Add a migration for model/schema changes.
- Apply migration locally with Alembic.
- Verify schema state and current revision.
- Validate migration through tests.

## Current Successful Migration Examples

This repo now includes revisions:
- `20260301_0002`: add node runtime tracking columns.
- `20260301_0003`: rename `linux_password_hash` to `linux_password` and enforce one manager per child node.
- `20260305_0008`: add `forms_ledger.version` optimistic-lock column.
- `20260306_0010`: rename `nodes.nullclaw_config_path` to `nodes.runtime_config_path` for the Nanobot runtime pivot.

Validated state in this repo:
- `uv run alembic current` => current revision at head
- `uv run pytest -q` => full suite green

## Procedure

1. Create or review migration file in `alembic/versions/`.
2. Run migration:
- `uv run alembic upgrade head`
3. Verify revision state:
- `uv run alembic current`
- `uv run alembic history --verbose`
4. Verify schema details:
- use `PRAGMA table_info(nodes)` for sqlite
- or run `.codex/skills/alembic-migration-ops/scripts/verify_m04_node_runtime_tracking.sh`
5. Run tests:
- `uv run pytest -q`

## Existing DB Recovery Pattern

If the DB schema exists but Alembic history is missing (common during transition from `create_all`):
1. `uv run alembic stamp 20260301_0001`
2. `uv run alembic upgrade head`

Use this only when you are certain the DB already matches the stamped revision.

## Startup Gate Troubleshooting

Kernel startup now enforces Alembic-head alignment and fails fast if DB revision is behind.

Recovery steps:
1. `uv run alembic current`
2. `uv run alembic upgrade head`
3. Restart kernel (`uv run python main.py`)

If startup still fails, confirm app is pointing at expected DB URL (`OMNICLAW_DATABASE_URL`).

## Verification Commands

```bash
uv run alembic upgrade head
uv run alembic current
python3 - <<'PY'
import sqlite3
conn = sqlite3.connect('workspace/omniclaw.db')
cur = conn.cursor()
cur.execute("PRAGMA table_info(nodes)")
for row in cur.fetchall():
    print(row)
conn.close()
PY
uv run pytest -q
```

## Related Skills

- `$authoring-skills`: structure and writing standards for skills.
- `$deploy-new-nanobot`: provisioning flow that depends on migrated DB state.
