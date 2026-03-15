---
name: draft-agent-business-case
description: Draft the complete BUSINESS_CASE request for a new agent deployment and submit it for HR review.
---

Stage: `BUSINESS_CASE`  
Allowed decision:
- `submit_to_hr`

## Goal
Create a complete, review-ready deployment request that HR and Finance can evaluate without guessing intent.

## Primary Template
- Use `templates/deploy_new_agent_business_case.md`.
- This is the full-form template with frontmatter plus required request sections.
- Downstream stages should append their own review sections; they must not overwrite this request content.

## Required Content
- Proposed agent role, mission, and scope boundaries.
- Why this role is needed now (business trigger and expected impact).
- Detailed task portfolio and ownership split.
- Required skills, tools, integrations, and safety constraints.
- Operating strategy (handoffs, escalation, and fallback plan).
- Success metrics and acceptance criteria.

## Steps
1. Copy `templates/deploy_new_agent_business_case.md` into `<workspace>/outbox/drafts/<file>.md`.
2. Fill frontmatter:
   - `form_type: deploy_new_agent`
   - `stage: BUSINESS_CASE`
   - `decision: submit_to_hr`
   - `subject: Deploy request - <role_name>`
   - leave `target` empty unless the workflow explicitly requires a dynamic target
3. Complete every section in the body template with concrete details.
4. Run a self-check:
   - A reviewer can understand role boundaries in one pass.
   - Required tooling and permissions are explicitly listed.
   - Risks and mitigations are concrete, not generic.
5. If complete, move file to `<workspace>/outbox/send/` and keep `decision: submit_to_hr`.

## When Not To Submit
Keep the form in draft if any are missing:
- unclear ownership boundaries
- no measurable success criteria
- missing required skill/tool list
- no mitigation plan for operational risks

## Validation Checklist
- Frontmatter matches current stage and decision.
- Request body includes role, strategy, tooling, risks, and measurable outcomes.
- Reviewer can choose `approve_to_finance` or `return_to_initiator` using evidence in the form.

## Fallback
- If kernel reports validation/routing issues, update frontmatter or missing sections and resubmit from `outbox/send/`.
