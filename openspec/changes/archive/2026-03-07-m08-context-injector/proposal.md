## Why

Deployed Nanobot agents currently receive a static `AGENTS.md` at provisioning time, which means manager edits, hierarchy changes, and inbox context do not flow back into the system prompt unless someone rewrites the workspace file manually. M08 introduces a kernel-owned context injector so supervisors can maintain external instruction templates while the kernel continuously renders a fresh, read-only `AGENTS.md` for active agents.

## What Changes

- Add a new instructions-management capability for external AGENTS templates, allowlisted `{{...}}` placeholder rendering, manager-scoped template access, and read-only rendered outputs.
- Extend canonical node metadata with `role_name` and `instruction_template_root` so provisioning and rendering share a stable source of truth.
- Update agent provisioning to create `workspace/nanobots_instructions/<node_name>/AGENTS.md`, persist the template root, and perform an initial render.
- Add a kernel instructions action surface for listing manageable targets, reading templates, previewing renders, updating templates, and syncing renders.
- Refresh rendered `AGENTS.md` files for active AGENT nodes at the start of every IPC scan cycle without blocking routed-form delivery when a render fails.
- Register and distribute one narrow manager skill for subordinate instruction management, backed by the new kernel actions.

## Capabilities

### New Capabilities
- `agent-instructions-management`: External AGENTS template storage, allowlisted placeholder rendering, hierarchy-based template access, and read-only rendered workspace prompts.

### Modified Capabilities
- `canonical-state-schema`: Persist instruction-template metadata and role metadata on canonical node records.
- `linux-provisioning`: Provisioning now creates external instruction template roots and renders initial AGENTS outputs from them.
- `file-ipc-router`: Scan cycles now run an AGENT render sweep before queued-form processing and isolate render failures from routing outcomes.

## Impact

- Affected code: `src/omniclaw/db/*`, `src/omniclaw/provisioning/*`, `src/omniclaw/ipc/*`, new `src/omniclaw/instructions/*`, `src/omniclaw/app.py`
- Affected APIs: new `POST /v1/instructions/actions`, extended provisioning payload for `role_name`
- Affected workspace assets: new `workspace/nanobots_instructions/`, new `workspace/company_config.json`, new manager instruction skill under `workspace/master_skills/`
- Verification impact: Alembic migration, new API/integration tests, IPC render-hook coverage, and updated operator/skill documentation
