---
name: request-nullclaw-agent-deployment
description: Agent SOP for drafting and submitting a nullclaw agent deployment approval request form to Macos_Supervisor, including required role/need/tasks/skills details.
license: MIT
compatibility: OmniClaw M06 forms actions + deployment request form type
metadata:
  author: omniclaw
  version: "0.1"
---

Use this skill when an AGENT needs approval to deploy a new nullclaw agent.

## Scope

This skill covers:
- bootstrapping the deployment-request form type definition in canonical DB state
- filling deployment-request business fields completely
- creating/submitting request draft to human approval stage
- resubmitting after rejection feedback
- keeping request payload actionable for provisioning follow-up

## Required Inputs

- `requester_node_id` (your node id)
- `candidate_node_name` (new agent node name)
- `requested_role` (job function of new agent)
- `business_need` (why deployment is required now)
- `expected_tasks` (specific tasks/workload to handle)
- `required_skills` (skills the new agent should run)

## Template

Primary template file:
- `.codex/skills/request-nullclaw-agent-deployment/templates/nullclaw_agent_deployment_request_form/request_draft.md`

## Execution Steps

1. Ensure the form type is active (`nullclaw_agent_deployment_request_form`).
2. Draft request content with the template fields completed.
3. Ensure objective criteria are clear:
   - role clarity
   - concrete business need
   - concrete tasks
   - candidate skills list
4. Create form instance (`create_form`) with initial holder as requester.
5. Submit decision decision `submit_for_review`.
6. If rejected, read decision note and update request details before resubmitting.

## Verification Commands

- Upsert form type:
  - `./scripts/forms/trigger_forms_action.sh --apply --body-file forms/nullclaw_agent_deployment_request_form.json`
- Validate form type:
  - `./scripts/forms/trigger_forms_action.sh --apply --action validate_form_type --type-key nullclaw_agent_deployment_request_form --version 1.1.0`
- Activate form type:
  - `./scripts/forms/trigger_forms_action.sh --apply --action activate_form_type --type-key nullclaw_agent_deployment_request_form --version 1.1.0`
- Run end-to-end smoke flow (dry-run then apply):
  - `./scripts/forms/smoke_nullclaw_agent_deployment_request.sh --requester-node-id <requester-id> --supervisor-node-id <supervisor-id>`
  - `./scripts/forms/smoke_nullclaw_agent_deployment_request.sh --apply --requester-node-id <requester-id> --supervisor-node-id <supervisor-id>`

## Fallback Path

If request is rejected:
1. Read reviewer decision note.
2. Update role/need/tasks/skills in draft.
3. Resubmit with `submit_for_review`.
