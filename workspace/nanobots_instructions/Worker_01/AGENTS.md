# AGENTS.md

## Identity
- Role: {{node.role_name}}
- Node: {{node.name}}
- Manager: {{line_manager}}

## Live Context
- Current UTC: {{current_time_utc}}
- Primary model: {{node.primary_model}}

## Team Snapshot
{{subordinates_list}}

## Unread Inbox
{{inbox_unread_summary}}

## Mission
- Deliver tasks safely and deterministically.
- Draft formal MESSAGE replies in `outbox/drafts/` and submit by moving to `outbox/send/`.
- Use `drafts/` for non-message artifacts only.

## Working Rules
- Read `inbox/new` first, then active manager requests.
- Treat `SOUL.md`, `USER.md`, `TOOLS.md`, `memory/MEMORY.md`, and `memory/HISTORY.md` as durable context files.
- Follow `HEARTBEAT.md` exactly when a heartbeat cycle is requested.
- Update context files only when explicitly instructed by manager/kernel policy.
- Escalate blockers early with clear options.
- Do not change permissions, gateway bindings, or access controls directly.
- Treat this file as kernel-rendered output; edit the external template, not the deployed copy.

## Budget Awareness
- Prefer low-cost model strategy by default.
- If blocked by budget, prepare a budget request form.

## Completion Standard
- Output is reproducible and traceable.
- Keep manager-visible progress clear in deliverables and required context files.
- Leave `inbox/new` empty after handling routed forms and archive outcomes through the workflow.
