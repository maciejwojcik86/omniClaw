## Why

Invalid queued forms currently stay in pending and get retried every scan, creating noise and repeated operator effort. The audit also identified duplicated resolver/manager-link code paths that can drift over time and cause inconsistent behavior.

## What Changes

- Change invalid-form handling from "stay in pending" to deterministic dead-letter + feedback routing.
- Generate kernel-authored feedback markdown with structured YAML error fields.
- Deliver feedback to resolved target inbox when possible; fall back to sender inbox when target is unresolved.
- Include dead-letter and feedback paths in IPC undelivered item response metadata.
- Add explicit requeue helper script for manual replay from dead-letter queue.
- Consolidate duplicated node-reference resolver logic and manager-link logic into shared repository/service helpers.

In scope:
- IPC undelivered file movement, feedback artifact generation, and metadata response updates.
- Requeue script and tests for replay flow.
- Internal dedupe refactor for resolver and manager-link paths.

Out of scope:
- Runtime/startup hardening (handled by archived `hardening-runtime-ipc-core`).
- New authorization model for who may requeue forms.
- Changes to stage skill distribution behavior.

## Capabilities

### New Capabilities
- `ipc-invalid-feedback-routing`: deterministic dead-letter, structured feedback routing, and explicit requeue control for invalid forms.

### Modified Capabilities
- `file-ipc-router`: undelivered filesystem lifecycle and scan response contract are updated.
- `canonical-state-schema`: form metadata fields for dead-letter tracking are exercised as active runtime contract.

## Impact

Affected code and systems:
- `src/omniclaw/ipc/service.py` (undelivered lifecycle and feedback write path).
- `src/omniclaw/db/repository.py`, `src/omniclaw/forms/service.py`, and shared resolver helpers for dedupe.
- `scripts/ipc/` (new requeue helper script).
- `tests/test_ipc_actions.py` and related regression fixtures.
