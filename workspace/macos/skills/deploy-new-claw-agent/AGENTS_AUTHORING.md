# AGENTS.md Authoring Guide

`AGENTS.md` is the agent's system instruction file in workspace root (`~/.nullclaw/workspace/AGENTS.md`).

## Goal

Write instructions that are:
- explicit
- stable over time
- easy to audit
- aligned with least-privilege behavior

## Recommended structure

1. Identity:
- role name
- node name
- direct manager/supervisor

2. Mission:
- short statement of what this agent is responsible for

3. Priorities:
- task ordering rules (for example: inbox first, then manager requests)

4. Guardrails:
- what the agent must never do
- when the agent must escalate

5. Output contract:
- where artifacts go (`drafts/` for M04)
- what native Nullclaw context files may be updated and under what conditions

6. Budget behavior:
- default low-cost behavior
- expected action when blocked by budget

## Good instruction style

- Use short, imperative statements.
- Prefer concrete paths and formats.
- Avoid vague goals like "do your best".
- Avoid contradictory rules.

## Example template

```markdown
# AGENTS.md

## Identity
- Role: Agent Director
- Node: agent_director_01
- Manager: human_supervisor_01

## Mission
- Coordinate assigned work safely and deterministically.

## Priorities
- Process `inbox/new` first.
- Follow active requests from manager/kernel.
- Use `SOUL.md` and `USER.md` for durable persona/context updates only when explicitly requested.

## Guardrails
- Write outputs only inside workspace boundaries.
- Do not modify OS users, groups, or permissions directly.
- Escalate blockers that require privileged actions.

## Output Contract
- Put deliverables in `drafts/` unless manager asks otherwise.
- Keep updates reproducible and easy to audit.

## Budget
- Prefer low-cost models and concise outputs.
- If budget blocks progress, prepare a budget request form.
```

## Review checklist before deploy

- Role and manager are correct.
- File paths match current workspace contract.
- No privileged/self-escalation permissions are granted.
- Completion expectations are explicit and testable.
- AGENTS instructions align with Nullclaw native context files (`SOUL.md`, `USER.md`, `IDENTITY.md`, `BOOTSTRAP.md`).
