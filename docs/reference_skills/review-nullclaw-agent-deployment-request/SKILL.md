---
name: review-nullclaw-agent-deployment-request
description: Human reviewer SOP for Macos_Supervisor to approve or reject nullclaw deployment requests with a decision note and deterministic workflow handoff.
license: MIT
compatibility: OmniClaw M06 forms actions + deployment request form type
metadata:
  author: omniclaw
  version: "0.1"
---

Use this skill when `Macos_Supervisor` reviews deployment requests at stage `WAITING_HUMAN_APPROVAL`.

## Scope

This skill covers:
- review criteria for deployment requests
- approval decision (`approve_deployment`)
- rejection decision (`reject_with_feedback`) with actionable feedback
- reject loop back to requester stage
- handoff to deployment execution SOP after approval

## Template

Primary template file:
- `.codex/skills/review-nullclaw-agent-deployment-request/templates/nullclaw_agent_deployment_request_form/waiting_human_approval.md`

## Review Criteria

- Is role definition specific and necessary?
- Is business need concrete and current?
- Are tasks clearly scoped and realistic?
- Are requested skills aligned with workload?
- Are risk/ownership notes sufficient?

## Execution Steps

1. Review request details against criteria.
2. Write decision note:
   - approval rationale; or
   - rejection gaps with required corrections
3. Submit one decision:
   - `approve_deployment` (terminal approval), or
   - `reject_with_feedback` (returns to requester draft stage)
4. For rejection, include `requester_node_id` in context so holder routes back correctly.
5. For approved requests, continue with `.codex/skills/deploy-new-claw-agent/SKILL.md` as the operational follow-up (M07 side effects are not auto-triggered in M06).

## Verification Commands

- Full lifecycle smoke sequence:
  - `./scripts/forms/smoke_nullclaw_agent_deployment_request.sh --requester-node-id <requester-id> --supervisor-node-id <supervisor-id>`

## Fallback Path

If decision is rejected by kernel:
1. Confirm actor is current holder (`Macos_Supervisor`).
2. Confirm decision key is valid for `WAITING_HUMAN_APPROVAL`.
3. For rejection flow, include valid `requester_node_id` context.
