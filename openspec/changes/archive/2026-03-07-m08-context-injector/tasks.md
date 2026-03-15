## 1. OpenSpec And Canonical State

- [x] 1.1 Finalize M08 proposal/spec/design docs and align session trackers for the active change.
- [x] 1.2 Add the Alembic revision plus canonical model/repository updates for `role_name` and `instruction_template_root`.

## 2. Provisioning And Instructions Service

- [x] 2.1 Extend provisioning to persist `role_name`, create external instruction template roots, seed default AGENTS templates, and render initial workspace `AGENTS.md`.
- [x] 2.2 Implement the new instructions module, request schemas, company-config loading, hierarchy authorization, template validation, and allowlisted render providers.
- [x] 2.3 Expose `POST /v1/instructions/actions` with `list_accessible_targets`, `get_template`, `preview_render`, `set_template`, and `sync_render`.

## 3. IPC Integration And Manager Tooling

- [x] 3.1 Add the whole-fleet AGENT render pre-pass to IPC scans with failure isolation from routed-form processing.
- [x] 3.2 Add the narrow manager instruction skill package, registration, and subordinate-based distribution bridge for M08.

## 4. Verification And Closure

- [x] 4.1 Add or update migration, provisioning, instructions API, IPC integration, and manager-skill tests.
- [x] 4.2 Update operator docs, project trackers, and project-local skills for the context-injector workflow.
- [x] 4.3 Run `uv run pytest -q` and `openspec validate --type change m08-context-injector --strict`, then mark the change ready for archive.
