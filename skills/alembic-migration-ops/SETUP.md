# Setup: Alembic Migration Ops Skill

## Prerequisites

- Python environment with project deps (`uv` recommended)
- `alembic` available in environment
- repository root as current working directory

## Validate toolchain

```bash
uv run alembic --help
uv run python -c "import sqlalchemy, alembic; print('ok')"
```

## Baseline config files

- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/*.py`

Do not manually edit the `alembic_version` table.

## Safety

- Prefer backup before production migrations (`cp workspace/omniclaw.db workspace/omniclaw.db.bak` for sqlite).
- Use `stamp` only for known-good baseline alignment, never as a substitute for running required migrations.
