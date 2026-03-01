## Context

M02 established persistent state; M03 adds host-level provisioning needed to turn logical nodes into runnable Linux-user agents. Because this involves privileged operations, the implementation must prioritize testability and operational safety.

## Goals / Non-Goals

**Goals:**
- Implement a provisioning service abstraction with `mock` and `system` adapters.
- Build deterministic workspace scaffolding logic for agent directories/files.
- Add permission application hooks for owner/group access behavior.
- Provide automated mock tests and manual system verification steps.

**Non-Goals:**
- Starting or managing Nullclaw services.
- Executing provisioning against production hosts automatically.
- Form/approval routing logic.

## Decisions

- Separate privileged command execution behind an adapter boundary.
- Use mock adapter as default in tests to avoid root requirements.
- Keep workspace scaffold as declarative constants to avoid path drift across modules.
- Deliver a manual system verification script for host-level validation outside CI.

## Risks / Trade-offs

- [Risk] Host permission differences across Linux distributions. -> Mitigation: keep system adapter explicit and provide manual verification checklist.
- [Risk] Privileged operations are unsafe if accidentally executed in tests. -> Mitigation: tests only use mock adapter; system adapter not used in CI.
- [Risk] Policy changes to folder structure create drift. -> Mitigation: centralize scaffold definition and validate with tests.
