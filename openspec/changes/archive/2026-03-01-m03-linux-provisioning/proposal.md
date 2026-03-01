## Why

With canonical state in place, OmniClaw now needs a controlled provisioning layer to create Linux users and workspace trees safely. M03 introduces the adapter pattern required for testable provisioning logic and staged rollout between mock and system execution.

## What Changes

- Add provisioning interfaces with `mock` and `system` adapters.
- Add workspace scaffold generation for required inbox/outbox/notes/journal/drafts/skills structure.
- Add ownership/group permission application logic for manager-worker access rules.
- Add mock-based automated tests and a manual system verification script.

## Capabilities

### New Capabilities
- `linux-provisioning`: Provides safe, testable Linux user/workspace provisioning primitives for agent onboarding.

### Modified Capabilities
- None.

## Impact

- Affected code: new provisioning modules under `src/omniclaw/`.
- Affected scripts: manual verification script for real-host validation.
- Enables M04 runtime bootstrap and subsequent workflow automation.
