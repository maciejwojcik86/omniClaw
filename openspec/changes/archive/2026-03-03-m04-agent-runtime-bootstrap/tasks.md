## 1. Runtime Bootstrap Foundations
> Legacy archive note: this historical checklist preserves original terminology from M04 implementation records.

- [x] 1.1 Add runtime configuration fields for command template, timeout, and output boundaries.
- [x] 1.2 Create runtime bootstrap service contract and command builder with user-context execution support and gateway start/stop/status actions.

## 2. Runtime Bootstrap Implementation

- [x] 2.1 Implement gateway launch/stop execution with metadata capture (timestamps, command, exit status, artifact paths).
- [x] 2.2 Expose kernel runtime control endpoint and response schema.
- [x] 2.3 Persist gateway running state and latest start/stop timestamps in kernel DB.

## 3. Verification and Documentation

- [x] 3.1 Add unit tests for runtime command building, metadata capture, and gateway state transitions.
- [x] 3.2 Add system smoke script and usage notes for gateway start/stop control.
- [x] 3.3 Add runtime-control skill documenting on/off endpoints for delegated operators (for example HR automation).
- [x] 3.4 Record deferred prompt-definition/onboarding-skill work in tracker backlog.
- [x] 3.5 Run `uv run pytest -q` and `openspec validate --type change m04-agent-runtime-bootstrap --strict`.

## 4. Human Supervisor Baseline and Line Management

- [x] 4.1 Add provisioning action to register existing kernel-running user as HUMAN node with repo-local workspace scaffold.
- [x] 4.2 Enforce manager requirement for `provision_agent` (manager node supports HUMAN or AGENT) and add action to link manager for existing agent rows.
- [x] 4.3 Update provisioning skill docs/payload samples with line-management SOP (`register_human`, `provision_agent` with manager, `set_line_manager`).
- [x] 4.4 Seed local baseline structure: register `macos` HUMAN node, create repo-local human workspace, and link manager for `Director_01` in SQLite.
