# Workflow: Applying and Verifying Alembic Migrations

## Inputs

- target revision (usually `head`)
- target database URL (default from `alembic.ini`)

## Steps

1. Inspect pending migrations
- `uv run alembic history --verbose`
- `uv run alembic current`

2. Apply
- `uv run alembic upgrade head`

3. Verify revision landed
- `uv run alembic current`

4. Verify schema change
- sqlite: `PRAGMA table_info(<table>)`
- run migration-specific verification script in this skill

5. Validate behavior
- `uv run pytest -q tests`

6. If Alembic history is missing but schema already exists
- `uv run alembic stamp <known_revision>`
- `uv run alembic upgrade head`
- re-check with `uv run alembic current`

## Rollback (if needed)

- one step: `uv run alembic downgrade -1`
- specific revision: `uv run alembic downgrade <revision_id>`

Use rollback only when you explicitly want to revert schema state.
