# OmniClaw Engineering Instructions

## Project Mission
OmniClaw builds a kernel that orchestrates repo-local Nanobot agents using formal Markdown/YAML forms, canonical database state, strict budget controls, and managed skill distribution.

## Skill-First Development Paradigm (Mandatory)
- Prefer modular, single-responsibility implementation steps over monolithic A-to-Z scripts.

## Skill Namespace Distinction And Mirroring Contract (Mandatory)
- There are two distinct skill families in this repo and they must not be conflated:
  - Developer/copilot skills live in `.codex/skills/` and mirrored `skills/`. These are for repo development by Codex CLI and nanobot itself. They should explain this repository, capture reusable development procedures, and serve as implementation/verification notes for continuing project work.
  - OmniClaw company/runtime skills live under workspace-managed locations such as `workspace/master_skills/` and `workspace/forms/<form_type>/skills/`. These are product/runtime artifacts intended for deployed OmniClaw agents and form workflows.
- Developer/copilot skill updates are mandatory closure work for implementation slices.
- Whenever a developer/copilot skill is created or updated in `.codex/skills/<skill-name>/`, mirror the same contents into `skills/<skill-name>/` in the same change so both toolchains read the same SOP.
- Do not treat workspace/company/form skills as substitutes for developer/copilot skills, and do not store developer workflow notes only inside workspace-managed skill locations.
- For host provisioning work, split by concern:
  - Linux user creation
  - Workspace scaffold creation
  - Ownership/group permission policy
- Use `$deploy-new-nanobot` as the default unified provisioning skill (workflow + setup + audit).
- Use `/home/macos/.nanobot/`, `/home/macos/nanobot/`, and the Nanobot deployment assets as the runtime/config reference baseline.
- Use `$runtime-gateway-control` for delegated gateway on/off/status endpoint workflows.
- Use `$alembic-migration-ops` when changing schema or verifying migration success.
- Every proven implementation pattern MUST be captured as a reusable developer/copilot skill under `.codex/skills/<skill-name>/SKILL.md` and mirrored to `skills/<skill-name>/SKILL.md`.
- Skills may reference helper scripts under `scripts/` and may call privileged kernel endpoints instead of running privileged commands directly when needed.
- Once a modular step is validated, keep the skill updated in the same change so the lesson is retained for future sessions.
- After every completed implementation slice (task/subtask/fix), run a Skill Delta Review:
  - If an existing skill covers the slice, update that skill with new SOP steps, command cheatsheet entries, and script references.
  - If no skill covers the slice, create a new focused skill immediately (modular SOP, not monolithic playbook).
  - Record reusable commands and helper scripts so other agents can repeat the workflow without rediscovery.

## Agent-Verifiable Testing Contract (Mandatory)
- When designing or validating operator workflows intended for Nanobot agents, prefer kernel endpoints and packaged helper scripts over direct repo inspection or ad hoc shell discovery.
- Do not rely on repository structure knowledge for workflows that agents are expected to run autonomously; if agent discovery, status, or reporting is needed, expose it through an endpoint or a committed script under `scripts/`.
- During testing, do not manually compensate for missing agent capabilities or permissions (for example deleting files, fixing ownership, or bypassing endpoint restrictions on the agent’s behalf) unless the explicit purpose of the test is break-glass operator recovery.
- Treat missing permissions, missing endpoints, or missing packaged scripts as product gaps to document and fix, not as obstacles to work around invisibly during validation.
- For every manual verification scenario that should later be executable by agents, define and prefer the canonical endpoint/script path first; only use repo-local exploratory commands for developer diagnosis, and clearly label them as non-canonical.

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
6. After each completed task, run Skill Delta Review and update/create developer/copilot skills in `.codex/skills`, mirror them into `skills/`, and update any referenced helper scripts.
7. Before archive, run a final OpenSpec Skill Review Gate to confirm all reusable lessons are captured as skill updates or new skills.

## OpenSpec Workflow Contract
Every milestone is one OpenSpec change and must follow this exact sequence:
1. `openspec new change <change-id>`
2. `openspec instructions proposal --change <change-id>` and author `proposal.md`
3. `openspec instructions specs --change <change-id>` and author `specs/**/*.md`
4. `openspec instructions design --change <change-id>` and author `design.md`
5. `openspec instructions tasks --change <change-id>` and author `tasks.md`
6. Implement only what is in `tasks.md`
7. Validate with `openspec validate --type change <change-id> --strict`
8. Run OpenSpec Skill Review Gate:
   - Review completed tasks for reusable workflows/operations.
   - Update existing skills or author new skills with SOP steps, verification commands, and fallback paths.
   - Add or refresh helper scripts referenced by those skills where repeatability warrants automation.
9. Archive with `openspec archive <change-id> -y`

## Task Tracking Contract
- Start every work session by reading `docs/current-task.md`.
- Keep exactly one active change at a time.
- After every completed task, update both:
  - `docs/plan.md`
  - `docs/current-task.md`
- After every completed task, also execute Skill Delta Review and update/create mirrored developer/copilot skill artifacts in `.codex/skills` and `skills/` in the same change.

## Skill Capture Contract
- When a workflow step is stable and repeatable, document it as a skill immediately.
- Skills must include: scope, required inputs, execution steps, verification commands, and fallback path.
- Prefer composing multiple focused skills rather than building a single all-in-one script.
- Keep helper scripts referenced by skills in `scripts/` and keep script usage examples current.
- Treat each skill as a modular SOP for future agents; include concise command cheatsheets for critical operator actions (for example provisioning and Linux permission control).
- Skill updates are mandatory closure work, not optional documentation cleanup.

## Definition of Done
A change is done only when all are true:
- `tasks.md` checklist reflects completed implementation.
- Relevant tests/checks pass.
- `openspec validate --type change <change-id> --strict` passes.
- `docs/current-task.md` and `docs/plan.md` are updated.
- OpenSpec Skill Review Gate is complete (existing skills updated and/or new skills created for reusable workflows).
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
- Nanobot runtime integration in dedicated milestones
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
- `src/omniclaw/budgets/`: waterfall budget engine, budget actions/service, and LiteLLM cap reconciliation.
- `src/omniclaw/instructions/`: AGENTS template management, rendering, and manager skill distribution.
- `src/omniclaw/ipc/`: file IPC router schemas/service for generic form scan/routing (`scan_forms`, `scan_messages` alias).
- `src/omniclaw/forms/`: form-type registry actions and graph-based state-machine decision service.
- `src/omniclaw/usage/`: LLM usage/session export persistence and API service.
- `tests/`: automated verification for API/runtime behavior.
- `.codex/skills/`: developer/copilot skills for Codex CLI; must mirror `skills/`.
- `skills/`: developer/copilot skills for nanobot runtime; must mirror `.codex/skills/`.
- `scripts/budgets/`: helper scripts for budget action triggers and manager budget operations.
- `scripts/provisioning/`: helper scripts used by provisioning-related skills and manual verification.
- `scripts/runtime/`: helper scripts for runtime gateway action triggers and smoke checks.
- `scripts/ipc/`: helper scripts for IPC router action triggers and form-routing checks.
- `scripts/forms/`: helper scripts for form-type administration, workspace workflow publication, and smoke checks.
- `workspace/`: repo-local supervisor/agent workspaces plus company-level form/skill artifacts.
  - `workspace/company_config.json`: company-level instructions and budgeting config.
  - `workspace/agents/`: deployed Nanobot agent directories (`<agent_name>/config.json` plus nested `workspace/`).
  - `workspace/forms/`: approved canonical form workflow packages (`<form_type>/workflow.json`).
  - `workspace/forms/<form_type>/skills/`: per-form stage skill master copies (`<required_skill>/...`).
  - `workspace/master_skills/`: approved master skills for company behavior bootstrapping.
  - `workspace/nanobot_workspace_templates/`: canonical deployed Nanobot workspace template source.
  - `workspace/nanobots_instructions/`: repo-local external instruction templates per node.
  - `workspace/form_archive/`: archived routed-form copies grouped by form type/id.
- `main.py`: temporary bootstrap entrypoint.
- `pyproject.toml`: Python project metadata.
- `uv.lock`: resolved dependency lockfile for reproducible `uv` runs.
- `README.md`: repository overview (to be expanded).

## Repository Map Maintenance Rules
- Update this map after every completed change.
- Update this map in the same change that introduces structural changes, new APIs, or schema/table changes.
- Do not defer map updates to later changes.
