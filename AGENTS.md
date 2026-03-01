# OmniClaw Engineering Instructions

## Project Mission
OmniClaw builds a kernel that orchestrates isolated Linux-user agents using formal Markdown/YAML forms, canonical database state, strict budget controls, and managed skill distribution.

## Skill-First Development Paradigm (Mandatory)
- Prefer modular, single-responsibility implementation steps over monolithic A-to-Z scripts.
- For host provisioning work, split by concern:
  - Linux user creation
  - Workspace scaffold creation
  - Ownership/group permission policy
- Every proven implementation pattern MUST be captured as a reusable skill under `.codex/skills/<skill-name>/SKILL.md`.
- Skills may reference helper scripts under `scripts/` and may call privileged kernel endpoints instead of running privileged commands directly when needed.
- Once a modular step is validated, keep the skill updated in the same change so the lesson is retained for future sessions.

## Canonical Source Order
Resolve requirements in this exact order:
1. `docs/current-task.md`
2. `docs/plan.md`
3. Active `openspec/changes/<change-id>/` artifacts (`proposal.md`, `specs/`, `design.md`, `tasks.md`)
4. `docs/OmniClaw PRD.md`
5. `docs/OmniClaw Implementation Roadmap.md`

Ignore `docs/universal_company_systems_→_agentic_translation.md` unless explicitly requested.
If items 4-5 do not exist yet, use `docs/early OmniClaw PRD.md` and `docs/old_stale/OmniClaw Implementation Roadmap.md`.

## Current Task References
- Active work card: `docs/current-task.md`
- Master backlog, milestone ledger, and risk register: `docs/plan.md`

## Long-Horizon Control Docs
Use these files to keep long-term execution coherent across sessions:
- `docs/plan.md`: Living multi-milestone execution plan, risk register, architecture notes, and status. Read at the start of every session and before changing milestones.
- `docs/prompt.md`: Master objective/spec prompt for Codex long-horizon execution. Read when resetting or redefining overall project execution intent.
- `docs/implement.md`: Strict implementation operating policy for milestone execution. Read immediately before coding inside an active change.
- `docs/documentation.md`: Living operator/developer documentation of what is actually implemented. Read before demos, handoffs, or onboarding.

## Execution Loop (per milestone)
Use this loop to maintain long-horizon context discipline:
1. Read `docs/plan.md` and identify the active milestone/change.
2. Write immediate approach and task-level TODOs in `docs/implement.md`.
3. Implement and test against active OpenSpec tasks.
4. Update `docs/documentation.md` with any new architecture or runtime behavior.
5. Update `docs/current-task.md` and `docs/plan.md` status/checklists.
6. Capture successful implementation patterns as reusable skills in `.codex/skills`.

## OpenSpec Workflow Contract
Every milestone is one OpenSpec change and must follow this exact sequence:
1. `openspec new change <change-id>`
2. `openspec instructions proposal --change <change-id>` and author `proposal.md`
3. `openspec instructions specs --change <change-id>` and author `specs/**/*.md`
4. `openspec instructions design --change <change-id>` and author `design.md`
5. `openspec instructions tasks --change <change-id>` and author `tasks.md`
6. Implement only what is in `tasks.md`
7. Validate with `openspec validate --type change <change-id> --strict`
8. Archive with `openspec archive <change-id> -y`

## Task Tracking Contract
- Start every work session by reading `docs/current-task.md`.
- Keep exactly one active change at a time.
- After every completed task, update both:
  - `docs/plan.md`
  - `docs/current-task.md`

## Skill Capture Contract
- When a workflow step is stable and repeatable, document it as a skill immediately.
- Skills must include: scope, required inputs, execution steps, verification commands, and fallback path.
- Prefer composing multiple focused skills rather than building a single all-in-one script.
- Keep helper scripts referenced by skills in `scripts/` and keep script usage examples current.

## Definition of Done
A change is done only when all are true:
- `tasks.md` checklist reflects completed implementation.
- Relevant tests/checks pass.
- `openspec validate --type change <change-id> --strict` passes.
- `docs/current-task.md` and `docs/plan.md` are updated.
- Repository map in this file is updated when structure/schema/API changed.

## Scope Guardrails
- One active milestone/change at a time.
- No out-of-scope work inside the active change.
- Advanced capabilities stay queued until their milestone becomes active.

## Tech Baseline
- Python 3.11+
- FastAPI kernel service
- SQLAlchemy + Alembic
- SQLite first, PostgreSQL compatibility path
- Nullclaw runtime integration in dedicated milestones
- LiteLLM integration in dedicated milestones

## Repository Map
Top-level map (update as project evolves):
- `AGENTS.md`: persistent engineering workflow and governance contract.
- `docs/`: product and execution docs.
  - `docs/OmniClaw PRD.md`: master product requirements and architecture intent.
  - `docs/OmniClaw Implementation Roadmap.md`: high-level implementation sequence.
  - `docs/plan.md`: canonical milestone backlog, risk register, and implementation plan.
  - `docs/current-task.md`: single active work card.
  - `docs/prompt.md`: long-horizon mission prompt for Codex project execution.
  - `docs/implement.md`: strict milestone implementation policy and verification rules.
  - `docs/documentation.md`: living implementation and operator documentation.
- `openspec/`: spec-driven change management.
  - `openspec/config.yaml`: schema, project context, and artifact rules.
  - `openspec/specs/`: canonical capability specs.
  - `openspec/changes/`: per-change proposal/specs/design/tasks artifacts.
- `alembic/`: migration environment and versioned schema migration scripts.
- `alembic.ini`: Alembic runtime configuration.
- `src/omniclaw/`: kernel Python package (app factory, config, logging, runtime modules).
- `tests/`: automated verification for API/runtime behavior.
- `.codex/skills/`: project-local reusable skills for modular implementation workflows.
- `scripts/provisioning/`: helper scripts used by provisioning-related skills and manual verification.
- `main.py`: temporary bootstrap entrypoint.
- `pyproject.toml`: Python project metadata.
- `uv.lock`: resolved dependency lockfile for reproducible `uv` runs.
- `README.md`: repository overview (to be expanded).

## Repository Map Maintenance Rules
- Update this map after every completed change.
- Update this map in the same change that introduces structural changes, new APIs, or schema/table changes.
- Do not defer map updates to later changes.
