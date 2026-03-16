## Why

OmniClaw currently mixes two partial skill-distribution models: hardcoded company manager skills and direct form-stage skill copies during workflow sync/routing. That leaves agent workspaces vulnerable to uncontrolled local edits, provides no canonical assignment ledger, and prevents companies from managing skill draft/approval/deactivation centrally.

## What Changes

- Introduce a kernel-managed master-skill lifecycle for all agent-visible skills, including loose company skills and form-linked stage skills.
- Add a canonical skill catalog and node-assignment ledger so the kernel can determine which skills each agent is allowed to hold.
- Add `POST /v1/skills/actions` for catalog management, batch assignment changes, and on-demand skill reconciliation.
- Reconcile each agent workspace `skills/` directory from DB-approved assignments during sync, removing stray agent-local skills.
- Update provisioning and `deploy_new_agent` to seed default company skills and expose post-deploy batch assignment workflows.
- Replace hardcoded manager-skill distribution with ordinary master-skill records and assignments.

## Capabilities

### New Capabilities
- `master-skill-lifecycle`: Catalog, lifecycle, assignment, and workspace reconciliation rules for OmniClaw master skills.

### Modified Capabilities
- `canonical-state-schema`: Extend canonical schema with master-skill lifecycle fields and node skill assignment state.
- `file-ipc-router`: Expand scan-time reconciliation to rebuild approved agent skills before routing.
- `agent-instructions-management`: Replace hardcoded manager-skill distribution with assignment-based manager skill delivery.
- `linux-provisioning`: Seed default company skills and initial skill sync during agent provisioning.
- `deploy-new-agent-workflow`: Extend deploy workflow guidance to include default skills and post-deploy batch assignment operations.

## Impact

- Affected code includes schema/models/repository, provisioning, IPC scan flow, form workflow sync/routing, and a new skills service/API module.
- Adds a new operator-facing endpoint family under `/v1/skills/actions` and packaged wrapper scripts under `scripts/skills/`.
- Adds new workspace master-skill packages plus developer/copilot skill documentation for continuing M11 work.
