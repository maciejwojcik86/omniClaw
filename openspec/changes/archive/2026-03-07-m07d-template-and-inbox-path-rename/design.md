## Context

The repo-local Nanobot pivot introduced a canonical workspace template source under `workspace/agent_templates` and kept the historical delivery folder name `inbox/unread`. Both names now conflict with the intended operator-facing model: the template root is Nanobot-specific, and routed work in the inbox is "new", not "unread". These strings are duplicated across provisioning code, IPC routing, canonical workflow skills, docs, and live copied skill bundles.

## Goals / Non-Goals

**Goals:**
- Rename the canonical Nanobot workspace template root to `workspace/nanobot_workspace_templates`.
- Rename the delivered inbox folder contract from `inbox/unread` to `inbox/new`.
- Keep canonical code, templates, tests, and workflow skills internally consistent.
- Preserve message acknowledge semantics by continuing to move files from `inbox/new` to `inbox/read`.

**Non-Goals:**
- No database migration.
- No changes to workflow graph semantics, holder resolution, or form frontmatter schema.
- No attempt to rewrite historical archived artifacts or agent memory logs.

## Decisions

### Rename the canonical template root in code and canonical assets
- Decision: move the template directory to `workspace/nanobot_workspace_templates` and update provisioning/deploy helpers to resolve that path directly.
- Rationale: the directory stores Nanobot-native workspace files and should be named accordingly.
- Rejected alternative: keep `workspace/agent_templates` and only update docs.
  - Rejected because it leaves the code contract mismatched to the intended runtime model.

### Rename the delivery inbox subdirectory to `new`
- Decision: change the runtime/config/scaffold default from `inbox/unread` to `inbox/new`.
- Rationale: it is clearer for operators and agents, and it avoids implying read-state semantics in the delivery folder name itself.
- Rejected alternative: keep the internal setting name and only symlink folders.
  - Rejected because it preserves misleading guidance and complicates tests/scripts for little value.

### Update canonical sources first, treat copied live bundles as secondary
- Decision: update `src/`, `scripts/`, `workspace/forms/`, `workspace/nanobot_workspace_templates`, and docs as the source of truth; only sync or patch live copied workspace bundles where needed for the local repo state.
- Rationale: canonical assets are what future workspace sync/provisioning uses.
- Rejected alternative: update only live workspace copies.
  - Rejected because the next sync or reprovision would reintroduce the old names.

## Risks / Trade-offs

- [Dirty working tree from prior work] → Limit edits to the requested rename surface and avoid reverting unrelated files.
- [Copied live skill bundles drift from canonical sources] → Update the canonical sources and the checked-in local copies that are already present in the repo workspace.
- [Breaking local operator habits/scripts] → Update docs, smoke scripts, and agent instructions in the same change.

## Migration Plan

1. Rename `workspace/agent_templates` to `workspace/nanobot_workspace_templates`.
2. Update provisioning/runtime/config code to use the new template root and `inbox/new`.
3. Update canonical workflow skills, heartbeat/AGENTS templates, scripts, docs, and tests.
4. Run targeted/full verification.

Rollback:
- Restore the prior directory name and revert the path constants in config/scaffold/scripts/docs.
- No stateful migration rollback is required because the change is path-based only.

## Open Questions

- None for implementation; the requested names are explicit.
