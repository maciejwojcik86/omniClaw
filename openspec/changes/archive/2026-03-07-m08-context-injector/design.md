## Context

OmniClaw currently provisions Nanobot workspaces with a placeholder `AGENTS.md` and then writes a static workspace prompt during deploy-tool execution. That leaves no canonical source for later edits, no kernel-owned templating pipeline, and no manager-facing API for instruction updates. The live codebase already has the necessary anchors for M08: canonical node/workspace metadata, a strict single-manager hierarchy, and a shared IPC scan path used for both manual and background routing cycles.

This change needs to touch multiple subsystems at once:
- canonical DB state and Alembic migration
- provisioning defaults and deploy workflow compatibility
- a new instructions service and API surface
- IPC scan integration for recurrent renders
- narrow master-skill registration/distribution for managers

## Goals / Non-Goals

**Goals:**
- Introduce a kernel-owned source-of-truth template root outside deployed workspaces for AGENT `AGENTS.md`.
- Render read-only workspace `AGENTS.md` files from allowlisted live context variables.
- Let managers discover, preview, and edit subordinate templates through kernel actions with hierarchy-based authorization.
- Refresh rendered AGENT instructions at the start of every IPC scan cycle within the existing <=5s routing cadence.
- Keep the implementation extensible so future files (`HEARTBEAT.md`, `SOUL.md`) can reuse the same template-root and rendering service.

**Non-Goals:**
- Generalize prompt templating to all markdown context files in this milestone.
- Deliver budget calculations, session-cost summaries, or higher-order computed providers beyond the allowlisted M08 variables.
- Build the full generic master-skill lifecycle planned for M11.
- Replace form-governed CAPA workflows; M08 only ships the direct manager tooling and its narrow manager skill.

## Decisions

### 1. Store template metadata directly on `nodes`
- Decision: add `role_name` and `instruction_template_root` columns to `nodes`.
- Rationale: provisioning, rendering, and runtime code already resolve AGENT state from `nodes`; keeping role/template metadata there avoids introducing a new table before multi-file templating exists.
- Rejected alternative: create a separate `instruction_templates` table now. Rejected because M08 only templates one file, and a new relational model would add migration/API complexity without immediate benefit.

### 2. Use `workspace/nanobots_instructions/<node_name>/AGENTS.md` as the source template root
- Decision: keep editable template sources outside agent workspaces in a repo-local instruction tree keyed by node name.
- Rationale: this matches the requirement that deployed Nanobots should not own their source instructions, while still keeping templates local, auditable, and easy for manager tooling to target.
- Rejected alternative: store the template inside the deployed workspace. Rejected because it weakens kernel control and lets agents overwrite their own future source prompt.

### 3. Add a dedicated instructions service and `POST /v1/instructions/actions`
- Decision: create a new `src/omniclaw/instructions/` module with its own request schema and service methods for `list_accessible_targets`, `get_template`, `preview_render`, `set_template`, and `sync_render`.
- Rationale: these actions are public kernel behaviors, not provisioning or IPC internals, and they need their own validation and authorization logic.
- Rejected alternative: extend `/v1/provisioning/actions`. Rejected because instructions management is an ongoing supervisor workflow, not a one-time provisioning concern.

### 4. Make hierarchy scope company-configurable via `workspace/company_config.json`
- Decision: load `instructions.access_scope` from `workspace/company_config.json`, supporting `direct_children` and `descendant`, with this repo defaulted to `descendant`.
- Rationale: the user explicitly wants both policies available per company, and a repo-local config file is the smallest stable configuration surface available today.
- Rejected alternative: hardcode one policy in the service. Rejected because it would force a code change for an organization-level governance choice.

### 5. Keep placeholder resolution allowlisted and strict
- Decision: support only the M08 variable set and reject unknown placeholders in `preview_render` and `set_template`; during auto-sync, preserve the last successful `AGENTS.md` if rendering fails.
- Rationale: strict validation keeps manager tooling debuggable and prevents silent prompt drift from typos.
- Rejected alternative: leave unknown placeholders literal or blank. Rejected because both options hide broken templates in production behavior.

### 6. Run the whole-fleet AGENT render sweep as a pre-pass in `_scan_forms()`
- Decision: invoke the instructions sync service at the start of `IpcRouterService._scan_forms()` for all active AGENT nodes.
- Rationale: manual and background IPC scans already share one execution path, so a pre-pass gives one implementation for both modes and matches the “fresh instructions every wake/scan” requirement.
- Rejected alternative: refresh only sender/holder nodes after successful route transitions. Rejected because it would skip idle agents and break the requirement that scan cycles refresh prompts even when no forms move.

### 7. Use live `inbox/new` files, not historical ledger paths, for unread summaries
- Decision: compute `{{inbox_unread_summary}}` from the actual workspace `inbox/new` directory.
- Rationale: live filesystem state is the authoritative unread queue, while older ledger rows may still point at legacy inbox locations from earlier milestones.
- Rejected alternative: derive unread state from `forms_ledger.delivery_path`. Rejected because it can be stale and mismatched to current workspace paths.

### 8. Ship one narrow manager instruction skill in M08
- Decision: add `workspace/master_skills/manage-agent-instructions/`, register it in `master_skills`, and distribute it only to nodes with a workspace plus at least one subordinate.
- Rationale: it satisfies the manager tooling requirement without prematurely generalizing the full validated-skill deployment engine.
- Rejected alternative: defer all skill distribution work to M11. Rejected because the user explicitly wants a manager-facing skill in M08.

## Risks / Trade-offs

- [Risk] Whole-fleet renders on every scan could slow high-frequency IPC cycles. → Mitigation: restrict sweep to active AGENT nodes, keep rendering file-local and dependency-free, and cover scan responsiveness in tests.
- [Risk] A bad manager template could wipe critical instructions. → Mitigation: reject unsupported placeholders on write, preserve the last good workspace `AGENTS.md` on sync failure, and surface detailed render errors.
- [Risk] Hierarchy traversal bugs could over-authorize template edits. → Mitigation: centralize authorization in the instructions service, test both `direct_children` and `descendant`, and never let the skill bypass service checks.
- [Risk] Narrow manager-skill distribution could age poorly before M11. → Mitigation: keep the registration/distribution helper isolated and document it as an M08-specific bridge to the later generic lifecycle.

## Migration Plan

1. Add Alembic revision for `nodes.role_name` and `nodes.instruction_template_root`.
2. Update repository and provisioning interfaces to read/write the new fields.
3. Add `workspace/company_config.json` with default `instructions.access_scope = "descendant"`.
4. Add the instructions service/API and wire it into the FastAPI app.
5. Update provisioning to create external instruction roots, seed default templates, register/distribute the manager skill, and render initial `AGENTS.md`.
6. Add the IPC render pre-pass and render-failure reporting.
7. Update tests, docs, and project-local skills, then run full verification.

Rollback:
- Revert the change and downgrade the Alembic revision.
- Remove the new instructions endpoint wiring and IPC pre-pass.
- Existing static workspace `AGENTS.md` files remain usable because the render path only overwrites from external templates after successful sync.

## Open Questions

- None for M08. Budget/session-summary providers and generic multi-file prompt templating remain deferred to later milestones by design.
