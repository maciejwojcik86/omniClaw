# Design: m12b-global-company-registry

## Canonical Model

### Global Config

The kernel reads one app-level config file:

- default path: `~/.omniClaw/config.json`

Structure:

```json
{
  "schema_version": 1,
  "companies": {
    "omniclaw": {
      "display_name": "OmniClaw",
      "workspace_root": "/home/macos/.omniClaw/workspace",
      "instructions": {
        "access_scope": "descendant"
      },
      "budgeting": {
        "daily_company_budget_usd": 3.0,
        "root_allocator_node": "Director_01",
        "reset_time_utc": "00:00"
      },
      "hierarchy": {
        "top_agent_node": "Director_01"
      },
      "skills": {
        "default_agent_skill_names": [
          "form_workflow_authoring"
        ]
      },
      "models": [
        {
          "id": "openai-codex/gpt-5.4",
          "name": "GPT 5.4 Codex"
        }
      ],
      "runtime": {
        "ipc_router_auto_scan_enabled": true,
        "ipc_router_scan_interval_seconds": 5,
        "budget_auto_cycle_enabled": true,
        "budget_auto_cycle_poll_interval_seconds": 60
      }
    }
  }
}
```

### Workspace

Each company workspace remains the home for editable/runtime assets only:

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

Workspace-local company config files are no longer canonical runtime inputs.

## Resolution Rules

### CLI

Canonical entrypoint:

```bash
omniclaw --company <slug-or-display-name>
```

Resolution order:

1. exact slug match
2. exact display-name match
3. case-insensitive unique display-name match

If no company is provided:

- auto-select only if the global config contains exactly one company
- otherwise fail with a clear error

### Compatibility

Legacy path/config overrides remain as low-level compatibility paths for tests and migration tooling, but they are no longer the documented startup contract.

### Missing Workspace

If the selected company entry points at a workspace root that does not exist, startup fails before app boot.

## Implementation

### New Config Layer

Add a dedicated global company registry loader/writer module and extend `Settings` to carry:

- `global_config_path`
- `company_slug`
- `company_display_name`
- `company_settings`

### Services

Refactor company-settings consumers to read from `Settings.company_settings` instead of loading a JSON file from the workspace:

- budgets
- instructions
- skills

Legacy workspace-config file loading remains only as compatibility fallback when `Settings` was constructed explicitly without a company registry entry.

### Scripts

Update canonical scripts to accept company references and optional global config path:

- runtime stack start
- direct run-agent helper
- invoke helpers
- workspace bootstrap/migration tools

### Migration

Migration/bootstrap scripts create or update `~/.omniClaw/config.json` company entries.

For existing workspaces:

- read legacy workspace config files if present
- read legacy model catalog if present
- write those settings into the global config entry
- keep the per-company SQLite DB in the workspace

## Validation

- strict OpenSpec validation
- config/build-path tests
- budget/instructions/skills tests against global config
- runtime script/CLI smoke using `--company`
