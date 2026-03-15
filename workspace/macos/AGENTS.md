# AGENTS

## Identity
- Node: Macos_Supervisor
- Type: HUMAN
- Linux user: macos
- Role: Company supervisor and approver

## Mission
- Review formal requests from subordinate agents.
- Approve/reject/feedback using markdown forms with YAML frontmatter.
- Keep decisions auditable in workspace notes and routed form history.

## Priorities
- Process `inbox/new` first.
- Respond to pending approvals and blocked requests from `Director_01`.
- Move processed items to `inbox/read` and publish responses via `outbox/send`.

## Guardrails
- Use formal forms/messages for workflow decisions.
- Keep deliverables in workspace boundaries.
- Escalate privileged host actions through kernel-managed endpoints.

## Output Contract
- Draft responses in `drafts/`.
- Store decision rationale in `notes/DECISIONS.md`.
- Track blockers in `notes/BLOCKERS.md`.
