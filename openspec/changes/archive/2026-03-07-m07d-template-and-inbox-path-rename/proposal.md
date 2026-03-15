## Why

The current filesystem contract still exposes two names that no longer match the intended Nanobot baseline: `workspace/agent_templates` is too generic, and `inbox/unread` is the wrong operator-facing name for newly delivered work. Renaming both now keeps the provisioning/runtime contract aligned before more workflow and context features build on these paths.

## What Changes

- **BREAKING** Rename the canonical Nanobot workspace template root from `workspace/agent_templates` to `workspace/nanobot_workspace_templates`.
- **BREAKING** Rename the routed-form delivery folder from `inbox/unread` to `inbox/new`.
- Update provisioning/runtime defaults, helper scripts, smoke tooling, canonical templates, and canonical workflow skills to use the new names.
- Update operator/developer documentation and active heartbeat guidance so agents are instructed against the new path contract.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `linux-provisioning`: provisioning workspace scaffolds and template sourcing change to the renamed Nanobot template root and delivery inbox folder.
- `file-ipc-router`: delivered forms and feedback artifacts use `inbox/new` as the canonical delivery folder.

## Impact

- Affected code: provisioning scaffold/config helpers, IPC router path resolution, deploy/message helper scripts, smoke scripts, and tests.
- Affected assets: canonical Nanobot workspace templates, canonical workflow skill packages, heartbeat/AGENTS guidance, and operator docs.
- No database or API schema changes are required; this is a filesystem contract rename.
