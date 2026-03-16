---
name: master-skill-lifecycle
description: Developer continuation notes for OmniClaw M11 master skill lifecycle architecture, decisions, and operating rules.
---

# Master Skill Lifecycle

## Scope

Use this skill when you need to continue, extend, or debug OmniClaw's M11 master skill lifecycle implementation.

## Concept

OmniClaw now treats every skill that can appear inside an agent workspace `skills/` directory as a kernel-controlled master skill. The source package may live in one of two places:

- loose company skill: `workspace/master_skills/<skill_name>/`
- form-linked stage skill: `workspace/forms/<form_type>/skills/<skill_name>/`

Both are cataloged in the shared `master_skills` table using:
- `master_path`: canonical source directory copied into workspaces
- `form_type_key`: owning form type for form-linked skills, `null` for loose company skills
- `lifecycle_status`: `DRAFT | ACTIVE | DEACTIVATED` for loose-skill lifecycle control

Naming constraint:
- `master_skills.name` is globally unique across loose and form-linked skills.
- If you need a loose/manual companion of a workflow-owned skill, give it a distinct name.
- Example: keep the form-linked `deploy-new-nanobot` under `workspace/forms/deploy_new_agent/skills/`, and publish a separate loose `deploy-new-nanobot-standalone` under `workspace/master_skills/` when managers need direct deployment capability.

## Core Data Model

- `master_skills`
  - shared catalog for loose and form-linked skills
  - `validation_status` remains for backward compatibility
  - `lifecycle_status` drives loose-skill assignment eligibility
- `node_skill_assignments`
  - one row per `node_id + skill_id + assignment_source`
  - `assignment_source` is `MANUAL`, `DEFAULT`, or `FORM_STAGE`
  - effective workspace skills are the union of all assignment rows for the node

Important consequence:
- deactivating a loose skill blocks new manual assignments
- existing assignment rows still reconcile until removed

## Runtime Flow

1. Loose company skills are cataloged by scanning `workspace/master_skills/*/SKILL.md`.
2. Form-linked skills are cataloged during form activation/workspace sync.
3. Provisioning seeds default loose skills from `workspace/company_config.json -> skills.default_agent_skill_names`.
4. Form activation refreshes `FORM_STAGE` assignment rows for the active workflow graph.
5. IPC scan pre-pass calls the shared skill reconciler before routing queued forms.
6. Reconciliation wipes only the agent workspace `skills/` directory and rebuilds it from assignment-approved catalog paths.

## Important Service Boundaries

- `src/omniclaw/skills/service.py`
  - owns catalog mutation, assignment mutation, and workspace reconciliation
- `src/omniclaw/instructions/service.py`
  - still owns AGENTS rendering
  - delegates manager-skill policy assignment to `SkillsService`
- `src/omniclaw/forms/service.py`
  - computes stage target sets
  - writes `FORM_STAGE` assignment rows instead of copying files directly
- `src/omniclaw/ipc/service.py`
  - uses the pre-pass to reconcile approved skills regularly
  - syncs affected target nodes through the shared reconciler instead of stage-file copy logic
- `src/omniclaw/provisioning/service.py`
  - seeds default loose skills
  - refreshes active form-skill assignments
  - performs initial skill sync for the new agent

## Operational Rules

- Only loose company skills are manually assignable through `/v1/skills/actions`.
- Form-linked skills are controlled by workflow ownership and `FORM_STAGE` assignment refreshes.
- Workspace drift is corrected by rebuilding the `skills/` directory from approved assignment state.
- Repo-root `.codex/skills/`, `skills/`, and `.agents/` are not governed by the runtime master-skill lifecycle.

## Canonical Tools

- endpoint: `POST /v1/skills/actions`
- wrappers:
  - `scripts/skills/trigger_skill_action.sh`
  - `scripts/skills/list_master_skills.sh`
  - `scripts/skills/list_active_master_skills.sh`
  - `scripts/skills/draft_master_skill.sh`
  - `scripts/skills/update_master_skill.sh`
  - `scripts/skills/set_master_skill_status.sh`
  - `scripts/skills/assign_agent_skills.sh`
  - `scripts/skills/remove_agent_skills.sh`
  - `scripts/skills/list_agent_skill_assignments.sh`
  - `scripts/skills/sync_agent_skills.sh`

## Verification

- migration/head:
  - `uv run alembic upgrade head`
  - `uv run alembic current`
- focused tests:
  - `PYTEST_ADDOPTS='-s' uv run pytest -q tests/test_schema_repository.py tests/test_skills_actions.py tests/test_forms_actions.py tests/test_provisioning_actions.py tests/test_instructions_actions.py tests/test_ipc_actions.py`
- change validation:
  - `openspec validate --type change m11-master-skill-lifecycle --strict`

## Fallback

- If agent skill sync removes something unexpectedly, inspect `node_skill_assignments` first; the workspace folder is derived output, not source of truth.
- If a loose skill cannot be assigned, confirm it is `ACTIVE` and `form_type_key` is `null`.
- If a form-linked skill is missing from a workspace, refresh the active form skill assignments and re-run agent skill sync.
