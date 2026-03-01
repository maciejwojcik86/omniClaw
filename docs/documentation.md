# OmniClaw Documentation

This is the living operator/developer documentation for OmniClaw.

## What OmniClaw Is

OmniClaw is a kernel that orchestrates autonomous coding agents as isolated Linux users.
It combines:
- Formal Markdown/YAML form-based communication
- Canonical relational state tracking
- Budget governance and quota controls
- Managed skill lifecycle and deployment

## Current Delivery Status

- M00: complete (governance bootstrap)
- M01: complete (kernel service skeleton)
- M02: complete (canonical state schema)
- M03: in progress (linux provisioning)

## Local Setup

Prerequisites:
- Python 3.11+
- `uv` installed

Install and run checks:
- `uv run pytest -q`
- `openspec validate --all --strict`

Run service (current baseline):
- `uv run python main.py`
- Health check: `GET http://localhost:8000/healthz`

## OpenSpec Workflow

Per milestone:
1. `openspec new change <change-id>`
2. Author artifacts:
   - `proposal.md`
   - `specs/**/*.md`
   - `design.md`
   - `tasks.md`
3. Implement scoped tasks
4. Validate:
   - `openspec validate --type change <change-id> --strict`
5. Archive:
   - `openspec archive <change-id> -y`

## Test, Lint, and Typecheck

Current mandatory verification:
- `uv run pytest -q`
- `openspec validate --all --strict`

Planned additions as codebase expands:
- lint command
- static typecheck command

## Repo Structure Overview

- `AGENTS.md`: persistent engineering contract and repository map.
- `docs/`: project and tracking docs (`current-task`, `plan`, PRD, roadmap).
- `openspec/`: specs and per-change artifacts.
- `src/omniclaw/`: kernel app, config, logging, DB, and domain modules.
- `alembic/` and `alembic.ini`: DB migration environment and versions.
- `tests/`: automated verification suites.
- `.codex/skills/`: project-local reusable skills.
- `scripts/provisioning/`: modular provisioning helper scripts (dry-run first).
- `docs/prompt.md`: long-horizon objective and build prompt for Codex.
- `docs/plan.md`: long-horizon execution plan, risks, and milestone status.
- `docs/implement.md`: strict implementation operating instructions.
- `docs/documentation.md`: this living operator/developer doc.

## Skill-First Provisioning Pattern (M03)

Provisioning is now organized as composable steps instead of one all-in-one script:
- Linux user creation
- Workspace scaffold creation
- Ownership/group permission application

Each step has:
- a reusable local skill in `.codex/skills/`
- a helper script in `scripts/provisioning/`
- dry-run default behavior before apply mode

## Privileged Provisioning Path

Recommended production-style flow:
- Keep FastAPI kernel unprivileged.
- Enable system provisioning endpoint mode with explicit flags.
- Route privileged host actions through:
  - `scripts/provisioning/privileged_provisioning_helper.sh`
- Allow only that helper in sudoers for the kernel service user.

Runtime env vars:
- `OMNICLAW_PROVISIONING_MODE=system`
- `OMNICLAW_ALLOW_PRIVILEGED_PROVISIONING=true`
- `OMNICLAW_PROVISIONING_HELPER_PATH=/abs/path/scripts/provisioning/privileged_provisioning_helper.sh`
- `OMNICLAW_PROVISIONING_HELPER_USE_SUDO=true`

## Data Model Overview (high level)

Canonical tables currently modeled:
- `nodes`
- `hierarchy`
- `budgets`
- `forms_ledger`
- `master_skills`

Key enums currently modeled:
- `NodeType`, `NodeStatus`
- `RelationshipType`
- `FormType`, `FormStatus`
- `SkillValidationStatus`

## Troubleshooting

1) `openspec validate` fails for a change
- Ensure required artifacts exist and requirement/scenario headers match schema expectations.
- Re-run: `openspec validate --type change <change-id> --strict`.

2) Tests fail due missing dependencies
- Run tests with `uv` so dependencies resolve via project metadata: `uv run pytest -q`.

3) Alembic migration import issues
- Confirm `alembic.ini` has `prepend_sys_path = .` and `path_separator = os`.
- Confirm `alembic/env.py` inserts `src/` into `sys.path`.

4) Runtime import issues in root entrypoint
- `main.py` prepends `src/` to `sys.path`; run from repository root.

## How to Use These Control Documents

- Start with `docs/prompt.md` when redefining or refreshing Codex mission instructions.
- Use `docs/plan.md` for milestone status, sequencing, risks, and architecture guidance.
- Use `docs/implement.md` as strict execution policy during implementation runs.
- Keep `docs/documentation.md` synchronized with actual shipped behavior.
