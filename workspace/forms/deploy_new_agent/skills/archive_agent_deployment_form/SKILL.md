---
name: archive_agent_deployment_form
description: Execute terminal ARCHIVED stage by appending final summary and ensuring closure-quality records.
---

Stage: `ARCHIVED` (terminal)  
Outgoing decisions: none

## Goal
Finalize the case record with a concise outcome summary and archive-ready metadata.

## Stage Template (Append-Only)
- Use `templates/archive_summary.md`.
- Append to the form body as the final section.
- Keep all earlier stages unchanged for full audit history.

## Outcome Modes To Document
- Deployment completed successfully.
- Deployment rejected during approvals.
- Deployment attempted but failed and closed.

## Steps
1. Read the full form history and identify final outcome mode.
2. Append `templates/archive_summary.md` with final summary details.
3. Ensure frontmatter remains terminal (`stage: ARCHIVED`) and do not set a new decision.
4. Save the finalized form to `<workspace>/outbox/pending/` if archival routing is required by your runtime.

## Validation Checklist
- `stage` is `ARCHIVED`.
- No new workflow decision is introduced.
- Archive summary includes outcome, key decisions, and artifact references.
