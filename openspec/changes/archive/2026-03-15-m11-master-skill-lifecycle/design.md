## Context

OmniClaw currently exposes two separate paths for agent skills. Organization-level manager skills are copied through a hardcoded instruction-service loop, while form stage skills are copied directly from workflow packages during activation and routing. Neither path records canonical per-agent assignments, and neither prevents agents from accumulating local skill drift inside their workspace `skills/` folder.

M11 needs to establish one kernel-owned lifecycle for all agent-visible skills without collapsing the distinction between loose company skills and form-linked skills. The current codebase already has a `master_skills` table with source paths and optional `form_type_key`, active IPC scan pre-passes, form graph target resolution, and provisioning hooks that can be extended instead of replaced.

## Goals / Non-Goals

**Goals:**
- Catalog all agent-visible skills in one canonical table, regardless of whether they live under `workspace/master_skills/` or `workspace/forms/<form_type>/skills/`.
- Track effective per-agent assignments in the database and rebuild workspace skill folders from that ledger.
- Add operator and manager-facing skill management actions under a dedicated API.
- Seed default loose skills during provisioning and preserve form-stage target semantics through durable `FORM_STAGE` assignments.
- Replace hardcoded manager-skill distribution with the same assignment-and-sync mechanism used for all other approved skills.

**Non-Goals:**
- Move form-linked skill source folders out of workflow packages.
- Make form-linked skills manually assignable or manually lifecycle-managed through the loose-skill API.
- Govern repo-root development skills under `.codex/skills/` or `skills/` through the runtime master-skill ledger.
- Introduce a second scheduling loop separate from the existing IPC scan pre-pass.

## Decisions

### 1. Reuse `master_skills` as the single catalog and add `node_skill_assignments` for effective delivery
- **Decision:** Keep `master_path` and `form_type_key` as the canonical source-of-truth location fields, add a new lifecycle enum to `master_skills`, and add a new `node_skill_assignments` table keyed by node, skill, and assignment source.
- **Rationale:** The repo already catalogs form-linked and manager skills in `master_skills`; extending that model is lower-risk than splitting into separate loose/form skill tables.
- **Rejected alternative:** Create separate tables for loose skills and form stage skills. Rejected because it duplicates catalog logic and makes reconciliation depend on merging two source systems.

### 2. Treat form-linked skills as first-class catalog entries but not generic lifecycle records
- **Decision:** Keep form-linked skill packages beside their forms, catalog them into `master_skills`, and generate `FORM_STAGE` assignments from workflow sync and routing events.
- **Rationale:** This preserves the current workspace package ergonomics while letting scan-time reconciliation restore approved stage skills after every wipe.
- **Rejected alternative:** Move all form-linked skills into `workspace/master_skills/`. Rejected because it breaks the current form-package ownership model and disconnects stage SOPs from their workflow assets.

### 3. Centralize workspace reconciliation in a dedicated skills service
- **Decision:** Add `src/omniclaw/skills/` to own catalog mutation, assignment mutation, effective-assignment queries, and filesystem reconciliation.
- **Rationale:** The current instructions service and form service each know too much about skill copying. A dedicated service isolates the new lifecycle and lets provisioning, IPC, and forms all reuse the same sync path.
- **Rejected alternative:** Leave copying logic split across instructions, forms, and IPC. Rejected because it would keep the current drift and make the assignment ledger informational only.

### 4. Use the IPC scan pre-pass as the canonical recurring sync point
- **Decision:** Extend the existing instruction pre-pass so it also reconciles approved workspace skills before routing.
- **Rationale:** The IPC scan loop already owns the recurring “prepare agent workspace” behavior. Reusing it avoids another scheduler and guarantees that stray skills are removed regularly.
- **Rejected alternative:** Add a separate periodic skill-sync loop. Rejected because it duplicates scheduling, observability, and failure handling.

### 5. Preserve immediate stage-skill usability by syncing affected nodes after form assignment updates
- **Decision:** When workflow activation or form routing changes `FORM_STAGE` assignments, sync the affected nodes immediately and still rely on scan-time reconciliation for durability.
- **Rationale:** Agents must have the required stage skill as soon as a form is delivered, not only on the next scan.
- **Rejected alternative:** Depend only on the next IPC scan pre-pass. Rejected because it can leave a target holder without the required local skill package during the same routing cycle.

### 6. Keep loose-skill defaults in company config
- **Decision:** Add `skills.default_agent_skill_names` to `workspace/company_config.json`, seeded with `form_workflow_authoring`, and apply those defaults during agent provisioning.
- **Rationale:** Default company skills are organization policy, not per-node mutable state, and the company config already holds similar governance defaults.
- **Rejected alternative:** Hardcode default loose skills in provisioning service. Rejected because it would require code changes for a company-level policy update.

## Risks / Trade-offs

- **[Assignment drift between forms and DB]** → Mitigation: replace direct form skill copies with durable `FORM_STAGE` assignment upserts/replacements and cover refresh behavior in form-sync and routing tests.
- **[Destructive workspace rebuilds remove needed files]** → Mitigation: scope reconciliation strictly to agent workspace `skills/`, rebuild from the approved ledger, and preserve source packages elsewhere in the repo.
- **[Manager authorization divergence]** → Mitigation: reuse the existing instruction hierarchy traversal rules for actor-scoped assignment actions.
- **[User worktree changes in existing skill assets]** → Mitigation: avoid reverting unrelated edits and only update the files necessary for the M11 behavior and documentation contract.

## Migration Plan

1. Add Alembic migration for new enums/columns and `node_skill_assignments`.
2. Backfill existing loose skill records under `workspace/master_skills/` into the new lifecycle as `ACTIVE`.
3. Backfill assignment rows for existing manager-facing skills based on the current subordinate graph so the new sync path preserves current behavior.
4. Extend repository/service/API code and switch provisioning, IPC, and form flows to the new assignment-based reconciliation path.
5. Add company and workflow skill packages plus wrapper scripts, then update docs and mirrored developer/copilot skills.
6. Validate with targeted tests, full pytest, and strict OpenSpec validation.

**Rollback**
- Downgrade the Alembic revision to remove the new schema elements.
- Revert the skills service/API wiring and restore the prior hardcoded manager-skill distribution plus direct form-stage copy behavior.
- Because source skill packages remain in place, rollback does not require regenerating workspace skill sources.

## Open Questions

- None for this slice. M11 intentionally keeps manual lifecycle control limited to loose company skills while form-linked skills remain governed by workflow ownership.
