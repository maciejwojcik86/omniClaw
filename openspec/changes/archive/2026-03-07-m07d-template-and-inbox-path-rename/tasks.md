## 1. Path Contract

- [x] 1.1 Rename the canonical Nanobot workspace template directory and update provisioning/runtime code to resolve `workspace/nanobot_workspace_templates`.
- [x] 1.2 Rename the delivered inbox contract from `inbox/unread` to `inbox/new` in config, scaffold helpers, and IPC/script path resolution.

## 2. Canonical Assets

- [x] 2.1 Update canonical workflow skills, templates, and heartbeat/AGENTS guidance to use the new template root and `inbox/new`.
- [x] 2.2 Update operator/developer docs and active change trackers/spec references that still encode the old names.

## 3. Verification

- [x] 3.1 Update or add tests and smoke-script assertions for the renamed paths.
- [x] 3.2 Run `uv run pytest -q`.
- [x] 3.3 Run `openspec validate --type change m07d-template-and-inbox-path-rename --strict`.
- [x] 3.4 Complete Skill Delta Review for the renamed Nanobot template/inbox contract.
