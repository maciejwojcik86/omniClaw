# OmniClaw Current Task

- active_change: `none`
- objective: Await next milestone selection after closing the global company registry change.

## last_completed_change
- change: `m12b-global-company-registry`
- archived_as: `openspec/changes/archive/2026-03-16-m12b-global-company-registry`
- closure_notes:
  - Replaced workspace-local company settings with one host-level OmniClaw registry at `~/.omniClaw/config.json`.
  - Made `omniclaw --company <slug-or-display-name>` the canonical kernel startup contract.
  - Migrated the local developer company into the registry, removed workspace-local company settings/model files, and archived the change after syncing canonical specs.

## next_focus
- No active change is selected.
- Next queued milestone in `docs/plan.md`: `m13-constitution-and-sop-pack`.

## blockers
- None currently known.

## current_status
- `m12-nanobot-monorepo-internalization` is archived at `openspec/changes/archive/2026-03-16-m12-nanobot-monorepo-internalization`.
- `m12b-global-company-registry` is archived at `openspec/changes/archive/2026-03-16-m12b-global-company-registry`.
- The implemented company config state is now:
  - `~/.omniClaw/config.json` is the only canonical company-settings source
  - `omniclaw --company <slug-or-display-name>` is the canonical startup contract
  - company workspaces keep editable assets and per-company SQLite state, but no longer own canonical company settings JSON

## next_up
- Select and open the next OpenSpec change before more implementation work begins.
- Keep the local registry-backed developer environment at `/home/macos/.omniClaw/config.json` and `/home/macos/.omniClaw/workspace` as the baseline for future work.
