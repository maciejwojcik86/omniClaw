---
name: verify-master-skill-lifecycle-live
description: Live validation SOP for M11 master-skill lifecycle using deployed repo-local agents, actor-scoped skill actions, and DB/workspace audits.
---

# Verify Master Skill Lifecycle Live

## Scope

Use this skill when you need to validate the M11 master-skill lifecycle against deployed repo-local agents instead of only pytest coverage.

## Required Inputs

- running OmniClaw kernel at `${OMNICLAW_KERNEL_URL:-http://127.0.0.1:8000}`
- deployed agents with repo-local workspaces, especially `Director_01` and `HR_Head_01`
- the packaged skill wrappers under `scripts/skills/`
- developer-side audit helper:
  - `scripts/skills/audit_agent_skill_state.sh`

## Two Validation Modes

### 1. Contract Mode

Use this when runtime prompt invocation is in `mock` mode or when you only need to prove the kernel contract.

In this mode you act through Director's authority using actor-scoped skill endpoints:
- `--actor-node-name Director_01`
- `--target-node-name HR_Head_01`

This proves:
- active-skill discovery
- descendant-scope authorization
- manual assignment/removal
- workspace reconciliation
- DB vs workspace agreement

### 2. Full Agent Mode

Use this only when `invoke_prompt` is not returning `mode: "mock"` and the agent is actually reasoning with tools.

In this mode:
1. Manually seed Director with the management skills.
2. Prompt Director through `scripts/runtime/invoke_agent_prompt.sh`.
3. Verify that Director chose the right tool path and that DB/workspace state changed correctly.

If `invoke_prompt` returns `mode: "mock"` or a `mock reply`, stop calling that an end-to-end agent test. Fall back to Contract Mode.

## Setup

1. Start the kernel:
   - `bash scripts/runtime/start_local_stack.sh`
2. Confirm active loose skills:
   - `bash scripts/skills/list_active_master_skills.sh --apply`
3. Seed Director with the M11 management skills:
   - `bash scripts/skills/assign_agent_skills.sh --apply --target-node-name Director_01 --skill-names "author-master-skill,manage-master-skills,manage-agent-skills"`
4. Audit Director and HR before the scenarios:
   - `bash scripts/skills/audit_agent_skill_state.sh --node-name Director_01 --node-name HR_Head_01`

## Example Live Scenarios

### Scenario A: Positive assignment through Director scope

Goal:
- Director grants HR the loose company skills `manage-agent-budgets` and `deploy-new-nanobot-standalone`

Contract-mode command:
- `bash scripts/skills/assign_agent_skills.sh --apply --actor-node-name Director_01 --target-node-name HR_Head_01 --skill-names "manage-agent-budgets,deploy-new-nanobot-standalone"`

Full-agent prompt:
- `bash scripts/runtime/invoke_agent_prompt.sh --apply --node-name Director_01 --session-key cli:m11-live-assign-positive --prompt "Use your manage-agent-skills skill to assign HR_Head_01 the active loose skills manage-agent-budgets and deploy-new-nanobot-standalone. After completing the assignment, reply with a short JSON object containing target_agent, assigned_skills, and whether the sync succeeded."`

Expected result:
- kernel accepts the assignment
- HR receives both skills in DB assignments
- HR workspace `skills/` contains both copied packages

### Scenario B: Read current HR skill state

Goal:
- Director reports HR's effective skill set

Contract-mode command:
- `bash scripts/skills/list_agent_skill_assignments.sh --apply --actor-node-name Director_01 --target-node-name HR_Head_01`

Full-agent prompt:
- `bash scripts/runtime/invoke_agent_prompt.sh --apply --node-name Director_01 --session-key cli:m11-live-list-hr-skills --prompt "Use your manage-agent-skills skill and its packaged tools to inspect HR_Head_01. Return only a JSON object with keys agent and skills. Each skills entry must contain name and assignment_sources."`

Expected result:
- returned skill names match the DB assignment ledger for HR

### Scenario C: Guardrail rejection for form-linked skill

Goal:
- prove Director cannot manually assign `deploy-new-nanobot`

Important:
- `deploy-new-nanobot` is a form-linked stage skill under `workspace/forms/deploy_new_agent/skills/`
- M11 intentionally forbids manual assignment of form-linked skills

Contract-mode command:
- `bash scripts/skills/assign_agent_skills.sh --apply --actor-node-name Director_01 --target-node-name HR_Head_01 --skill-names "deploy-new-nanobot"`

Full-agent prompt:
- `bash scripts/runtime/invoke_agent_prompt.sh --apply --node-name Director_01 --session-key cli:m11-live-assign-negative --prompt "Try to assign HR_Head_01 the skill deploy-new-nanobot using your skill-management tools. If the kernel rejects it, explain briefly why and do not invent a workaround."`

Expected result:
- kernel rejects the action
- no DB assignment row is created for `deploy-new-nanobot`
- no new `deploy-new-nanobot` directory appears in HR's workspace `skills/`

## Verification

1. Read HR assignments through the kernel:
   - `bash scripts/skills/list_agent_skill_assignments.sh --apply --target-node-name HR_Head_01`
2. Compare DB desired state vs deployed workspace state:
   - `bash scripts/skills/audit_agent_skill_state.sh --node-name HR_Head_01`
3. Inspect the raw workspace if needed:
   - `find /home/macos/omniClaw/workspace/agents/HR_Head_01/workspace/skills -maxdepth 2 -type f | sort`

Completion standard:
- positive scenario skills appear in both DB and workspace
- negative scenario skill appears in neither
- audit output reports `matches: true`

## Fallback

- If the kernel is unreachable, start it and rerun the scenario.
- If `invoke_prompt` returns `mode: "mock"`, do not claim an agent-behavior test passed; use Contract Mode instead.
- If the audit shows drift, rerun:
  - `bash scripts/skills/sync_agent_skills.sh --apply --target-node-name <agent_name>`
- If a scenario should leave the environment clean, remove the test skills after verification:
  - `bash scripts/skills/remove_agent_skills.sh --apply --actor-node-name Director_01 --target-node-name HR_Head_01 --skill-names "manage-agent-budgets,deploy-new-nanobot-standalone"`
