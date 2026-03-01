---
name: provision-workspace-scaffold
description: Create the OmniClaw agent workspace directory and seed files as a standalone, idempotent step.
license: MIT
compatibility: Python 3.11+
metadata:
  author: omniclaw
  version: "0.1"
---

Provision exactly one concern: workspace shape.

Use this skill after user identity exists. Do not apply ownership policy here.

## Inputs

- `workspace_root` (required)

## Steps

1. Preview file-system actions:
   - `uv run python scripts/provisioning/create_workspace_tree.py --workspace-root <path>`
2. Apply creation:
   - `uv run python scripts/provisioning/create_workspace_tree.py --apply --workspace-root <path>`
3. Verify expected paths exist:
   - `inbox/unread`, `inbox/read`
   - `outbox/pending`, `outbox/drafts`, `outbox/sent`
   - `notes`, `journal`, `metrics`, `drafts`, `skills`
   - `notes/TODO.md`, `notes/DECISIONS.md`, `notes/BLOCKERS.md`
   - `persona_template.md`, `AGENTS.md`

## Kernel endpoint fallback

For remote or restricted hosts, use:
- `scripts/provisioning/trigger_kernel_action.sh --payload-file <json-file>`

Example payload:
```json
{
  "action": "create_workspace",
  "workspace": {
    "root": "/home/agent_director_01/workspace",
    "scaffold": true
  }
}
```

## Output contract

Return concise status with:
- root path
- created vs already-existing directories/files
