# OmniClaw Current Task

- active_change: `none`
- objective: `m07b-nanobot-runtime-migration` is archived; hold the line on the Nanobot runtime baseline and prepare the next approved change.

## in_scope
- Keep docs, skills, and canonical workflow assets aligned with the archived Nanobot runtime baseline.
- Preserve repo-local AGENT directory semantics under `workspace/agents/<agent_name>/`.
- Prepare the next active change only when explicitly approved.

## out_of_scope
- New implementation work without an opened OpenSpec change.
- Reverting the Nanobot runtime pivot back to Nullclaw defaults.

## tasks
- [x] Archive `m07b-nanobot-runtime-migration` as `2026-03-06-m07b-nanobot-runtime-migration`.
- [x] Sync archived delta specs into `openspec/specs/`.
- [x] Re-run strict verification before archive (`uv run pytest -q`, `openspec validate --type change m07b-nanobot-runtime-migration --strict`).

## blockers
- None.

## acceptance_checks
- [x] `uv run pytest -q` passes (`63 passed`).
- [x] `openspec validate --type change m07b-nanobot-runtime-migration --strict` passes.
- [x] OpenSpec archive completed with spec sync.

## next_up
- Open the next approved change, likely `m08-context-injector`, when ready.
