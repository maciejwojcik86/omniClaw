---
name: final-agent-signoff
description: Execute DIRECTOR_APPROVAL for deploy_new_agent and choose deployment, rework, or rejection.
---

Stage: `DIRECTOR_APPROVAL`  
Allowed decisions:
- `execute_deployment`
- `return_to_finance`
- `reject`

## Goal
Make the final decision based on business value, financial viability, and operational risk.

## Stage Template (Append-Only)
- Use `templates/director_signoff.md`.
- Append this section to the existing form body.
- Keep all previous stage content intact for audit traceability.

## Decision Rules
- Choose `execute_deployment` when:
  - business case, HR review, and finance review are all coherent
  - residual risk is acceptable
  - deployment constraints are clear
- Choose `return_to_finance` when:
  - cost assumptions or budget controls need refinement
  - financial risk is unresolved
- Choose `reject` when:
  - request is strategically misaligned
  - expected value does not justify risk/cost
  - unresolved critical concerns remain

## Steps
1. Review the full history from BUSINESS_CASE through FINANCE_REVIEW.
2. Evaluate strategic fit, risk posture, and delivery readiness.
3. Append `templates/director_signoff.md` with explicit decision rationale.
4. Set frontmatter `decision` to one allowed decision.
5. Save updated form to `/outbox/send/`.

## Quality Requirements
- Decision must include non-generic rationale tied to evidence in prior sections.
- If returning/rejecting, include clear corrective guidance or closure reason.

## Validation Checklist
- `stage` remains `DIRECTOR_APPROVAL`.
- Decision value is valid for this stage.
- Appended signoff section includes rationale and constraints.
