# Company Workspace Ops

## Scope
- Register OmniClaw companies in the host-level registry at `~/.omniClaw/config.json`.
- Bootstrap or migrate a company workspace without keeping company settings inside the workspace.
- Verify that runtime paths, budgets, skills, and templates resolve through the registry entry.

## Required Inputs
- Company slug, for example `omniclaw`.
- Optional company display name.
- Target company workspace root.
- Optional source workspace root when migrating legacy repo-local state.

## Canonical Defaults
- Global OmniClaw config: `~/.omniClaw/config.json`
- Default OmniClaw company workspace: `~/.omniClaw/workspace`
- Canonical startup: `omniclaw --company <slug-or-display-name>`

## Execution Steps
1. Bootstrap or refresh a registered company workspace:
   - `uv run python scripts/company/bootstrap_company_workspace.py --apply --company omniclaw --display-name "OmniClaw" --company-workspace-root "$HOME/.omniClaw/workspace"`
2. Migrate the legacy repo-local seed workspace into a registered company root when needed:
   - `uv run python scripts/company/migrate_repo_workspace.py --apply --force --company omniclaw --global-config-path "$HOME/.omniClaw/config.json" --source-workspace-root /home/macos/omniClaw/workspace --company-workspace-root "$HOME/.omniClaw/workspace"`
3. Inspect the resolved company context:
   - `uv run python scripts/company/show_company_context.py --company omniclaw`
4. Start the kernel against the registered company:
   - `bash scripts/runtime/start_local_stack.sh --company omniclaw`
5. Verify DB-backed runtime state and deployed skills:
   - `uv run python scripts/provisioning/list_agents_permissions.py --company omniclaw`
   - `uv run python scripts/skills/audit_agent_skill_state.py --company omniclaw`

## Verification
- `~/.omniClaw/config.json` contains the company entry with `workspace_root`, budgeting, hierarchy, skills, models, and runtime sections.
- `<company-workspace-root>/omniclaw.db` exists and agent path columns point at the selected workspace.
- The company workspace does not need `config.json`, `company_config.json`, or `models/company_models.yaml` as runtime truth.
- `scripts/skills/audit_agent_skill_state.py` reports `matches: true` after reconciliation.

## Fallback
- If the registry is missing or the wrong company is selected, rerun `show_company_context.py` before booting the kernel.
- If the workspace root is not ready yet, use the bootstrap script first instead of starting `omniclaw`.
- If a legacy tool still expects raw paths, use the compatibility overrides `--company-workspace-root` and `--company-config-path` temporarily, then move back to the registry contract.
