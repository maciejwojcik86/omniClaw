# AGENTS.md Authoring Guide

`AGENTS.md` is the agent's system instruction file in workspace root (`workspace/agents/<agent_name>/workspace/AGENTS.md`).

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
- where artifacts go (`drafts/` for general deliverables, `outbox/` for routed forms/messages)
- what Nanobot and OmniClaw context files may be updated and under what conditions

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
- Node: Director_01
- Manager: Macos_Supervisor

## Mission
- Coordinate assigned work safely and deterministically.

## Priorities
- Process `inbox/unread` first.
- Follow active requests from manager/kernel.
- Use `SOUL.md`, `USER.md`, `TOOLS.md`, `memory/MEMORY.md`, and `memory/HISTORY.md` for durable context updates only when explicitly requested.
- Treat `sessions/` as runtime-owned unless a specific maintenance task says otherwise.

## Guardrails
- Write outputs only inside workspace boundaries.
- Do not modify OS users, groups, or permissions directly.
- Escalate blockers that require privileged actions.

## Output Contract
- Put deliverables in `drafts/` unless manager asks otherwise.
- Put routed forms/messages in `outbox/drafts/` or `outbox/pending/`.
- Keep updates reproducible and easy to audit.

## Budget
- Prefer low-cost models and concise outputs.
- If budget blocks progress, prepare a budget request form.
```

## Review checklist before deploy

- Role and manager are correct.
- File paths match the repo-local Nanobot workspace contract.
- No privileged/self-escalation permissions are granted.
- Completion expectations are explicit and testable.
- AGENTS instructions align with Nanobot native context files (`SOUL.md`, `USER.md`, `TOOLS.md`, `HEARTBEAT.md`, `memory/`) and OmniClaw routing folders (`inbox/`, `outbox/`, `drafts/`).
