# OmniClaw

OmniClaw is a kernel that orchestrates Nanobot agents from one selected company workspace, with formal form routing, DB-backed state, budget controls, and kernel-managed skill distribution.

## Install

```bash
bash scripts/install/bootstrap_monorepo.sh
```

That installs both packaged CLIs from this monorepo:

- `omniclaw`
- `nanobot`

## Company Registry

OmniClaw now uses one host-level config as the only source of truth:

- `~/.omniClaw/config.json`

Each company entry stores:

- `display_name`
- `workspace_root`
- budgeting settings
- hierarchy anchors
- default skills
- models
- runtime settings

The company workspace keeps editable assets and runtime data only:

- `agents/`
- `forms/`
- `master_skills/`
- `nanobots_instructions/`
- `nanobot_workspace_templates/`
- `form_archive/`
- `logs/`
- `retired/`
- `runtime_packages/`
- `finances/`
- `omniclaw.db`

## Start The Kernel

```bash
uv run omniclaw --company omniclaw
```

Or via the wrapper:

```bash
bash scripts/runtime/start_local_stack.sh --company omniclaw
```

If `.env` points `LITELLM_PROXY_URL` at `localhost` or `127.0.0.1`, OmniClaw auto-starts the local LiteLLM proxy and stops it on exit.

Health check:

```bash
curl -s http://127.0.0.1:8000/healthz
```

## Register Or Migrate A Company

Bootstrap a registered workspace:

```bash
uv run python scripts/company/bootstrap_company_workspace.py \
  --apply \
  --company omniclaw \
  --display-name "OmniClaw" \
  --company-workspace-root "$HOME/.omniClaw/workspace"
```

Migrate the legacy repo-local seed workspace:

```bash
uv run python scripts/company/migrate_repo_workspace.py \
  --apply \
  --force \
  --company omniclaw \
  --source-workspace-root /home/macos/omniClaw/workspace \
  --company-workspace-root "$HOME/.omniClaw/workspace"
```

Inspect the resolved company context:

```bash
uv run python scripts/company/show_company_context.py --company omniclaw
```

## Run An Agent

```bash
bash scripts/runtime/run_agent.sh --company omniclaw --agent-name Director_01 --message "Hello"
```

Or call Nanobot directly against the deployed agent workspace/config:

```bash
nanobot agent -w "$HOME/.omniClaw/workspace/agents/Director_01/workspace" -c "$HOME/.omniClaw/workspace/agents/Director_01/config.json" -m "Hello"
```
