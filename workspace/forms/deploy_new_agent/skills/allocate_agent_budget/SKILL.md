---
name: allocate_agent_budget
description: Perform FINANCE_REVIEW for deploy_new_agent and decide whether budget is approved or returned to HR.
---

Stage: `FINANCE_REVIEW`  
Allowed decisions:
- `approve_to_director`
- `return_to_hr`

## Goal
Decide whether the deployment is financially feasible and sufficiently justified to move to director approval.

## Stage Template (Append-Only)
- Use `templates/finance_review.md`.
- Append the template section to the existing form body.
- Do not replace prior sections from BUSINESS_CASE or HR_REVIEW.

## Decision Rules
- Choose `approve_to_director` when:
  - cost model is realistic and internally consistent
  - funding source is clear
  - expected value justifies operating cost
  - risk-adjusted budget is acceptable
- Choose `return_to_hr` when:
  - assumptions are missing or contradictory
  - budget source/ownership is unclear
  - proposal needs scope adjustment before approval

## Steps
1. Read request plus HR findings from `inbox/unread/`.
2. Evaluate cost assumptions, expected utilization, and funding source.
3. Append `templates/finance_review.md` with concrete numbers and rationale.
4. Set frontmatter `decision`:
   - `approve_to_director` or `return_to_hr`
5. Save updated form to `<workspace>/outbox/pending/`.

## Quality Requirements
- Use explicit numeric ranges where possible.
- Explain major assumptions behind estimates.
- If returning, state exactly what HR/initiator must revise.

## Validation Checklist
- `stage` remains `FINANCE_REVIEW`.
- `decision` is valid for this stage.
- Finance section includes recommendation, rationale, and constraints.
