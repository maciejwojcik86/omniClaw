Active implementation change: `none`

Implementation focus

1. Keep the repo in the archived M12b state until the next OpenSpec change is selected.
2. Use the registry-backed local company environment as the baseline for future milestones.

Status

- `m12-nanobot-monorepo-internalization` was archived on 2026-03-16 after its spec sync and validation were complete.
- `m12b-global-company-registry` was archived on 2026-03-16.
- OmniClaw now uses one app-level config at `~/.omniClaw/config.json`, with company workspaces reduced to editable assets and per-company runtime state.
- Root pytest is intentionally scoped to `tests/`; vendored Nanobot upstream tests remain opt-in and should be run from `third_party/nanobot/` with that package's dev extras when needed.

Archived Outcome

- Canonical startup becomes `omniclaw --company <slug-or-display-name>`.
- Company-wide settings come from the global registry, not from workspace-local `config.json` / `company_config.json`.
- Workspaces continue to own text assets, forms, skills, templates, archives, logs, and the per-company SQLite DB.

Validation evidence

- `openspec validate --type change m12b-global-company-registry --strict`
- `PYTEST_ADDOPTS='-s' uv run pytest -q tests` (`101 passed in 185.58s`)
- `env OMNICLAW_LITELLM_AUTO_START_LOCAL_PROXY=false timeout 10s uv run omniclaw --company omniclaw --host 127.0.0.1 --port 8012` (startup completed; timeout used to stop the server after smoke validation)

Notes

- M12b can keep low-level compatibility paths for tests and migration tooling, but the documented operator contract should move fully to the global company registry.
