---
name: deploy_new_claw_agent_stage
description: Execute AGENT_DEPLOYMENT stage and record technical deployment evidence before archival.
---

Stage: `AGENT_DEPLOYMENT`  
Allowed decision:
- `deploy_and_archive`

## Goal
Run the approved deployment, capture evidence, and move the form to terminal archival.

## Stage Template (Append-Only)
- Use `templates/deployment_execution.md`.
- Append the execution log section to the existing form.
- Do not rewrite approval history.

## Preconditions
- Director decision selected `execute_deployment`.
- Deployment constraints are documented in prior sections.
- Required provisioning toolchain is available.

## Steps
1. Read constraints and required agent profile from the form.
2. Execute approved deployment workflow (scripts/endpoints).
3. Collect execution evidence (commands used, outputs, IDs, timestamps).
4. Append `templates/deployment_execution.md` with concrete execution details.
5. If deployment succeeded, set `decision: deploy_and_archive`.
6. Save updated form to `<workspace>/outbox/pending/`.

## Recommended Tooling
- `scripts/provisioning/deploy_new_claw_agent.sh`
- `scripts/provisioning/trigger_kernel_action.sh`

## Failure Handling
- If deployment fails, keep form in `AGENT_DEPLOYMENT` (do not force decision).
- Append blocker details and remediation attempts to the deployment section.
- Escalate failure to supervisor according to local operating policy.

## Validation Checklist
- `stage` remains `AGENT_DEPLOYMENT`.
- Decision is set to `deploy_and_archive` only after successful execution.
- Deployment section includes verifiable evidence and follow-up actions.
