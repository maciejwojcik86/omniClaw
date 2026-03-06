---
name: review-agent-role-and-template
description: Perform HR_REVIEW for deploy_new_agent forms and decide whether to move to finance or return for revision.
---

Stage: `HR_REVIEW`  
Allowed decisions:
- `approve_to_finance`
- `return_to_initiator`

## Target

Director_01

## Goal
Confirm the requested role is well-defined, safe to operate, and documented well enough for budget and final approval review.

## Stage Template (Append-Only)
- Use `templates/hr_review.md`.
- Append this section to the existing form body.
- Do not delete or rewrite previous stages; this stage adds HR evaluation and decision rationale.

## Decision Rules
- Choose `approve_to_finance` when:
  - role mission and boundaries are clear
  - scope is actionable and not contradictory
  - required skills/tools are realistic and traceable
  - success metrics are reviewable
- Choose `return_to_initiator` when:
  - role or boundaries are ambiguous
  - tasks are missing details or ownership
  - required constraints/instructions are incomplete
  - the request cannot be evaluated reliably

## Steps
1. Read the full request from `inbox/unread/`.
2. Evaluate role clarity, scope boundaries, and instruction quality.
3. Append `templates/hr_review.md` with concrete findings.
4. Set `decision` in frontmatter:
   - `approve_to_finance` or `return_to_initiator`
5. Save updated form to `/outbox/pending/`.

## Quality Requirements
- Feedback must be specific and actionable.
- If returning to initiator, include exact revision requests.
- Avoid generic approval statements without evidence.

## Validation Checklist
- Form frontmatter remains `stage: HR_REVIEW`.
- Decision is one of allowed values for this stage.
- Appended HR review section explains why this decision was chosen.
