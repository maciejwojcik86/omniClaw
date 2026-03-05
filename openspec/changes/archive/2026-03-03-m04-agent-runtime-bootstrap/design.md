## Context

M03 established OS-level provisioning and permission policy, including real system-mode user/workspace creation through kernel endpoints. M04 must now prove that a provisioned agent can run a restricted Nullclaw execution path and produce draft artifacts while preserving safety boundaries. Nullclaw references indicate config in `~/.nullclaw/config.json` and workspace in `~/.nullclaw/workspace`, so runtime bootstrap paths must align with that contract.

## Goals / Non-Goals

**Goals:**
- Implement a runtime bootstrap service callable from the kernel.
- Run Nullclaw gateway start/stop actions under the provisioned agent Linux user.
- Use native Nullclaw workspace context files without introducing M04 prompt-seed creation logic.
- Capture execution metadata for each run.
- Track gateway running state and latest start/stop timestamps in kernel DB.
- Register the kernel-running Linux user as a HUMAN node with repo-local workspace.
- Enforce AGENT line-management linkage for provisioning baseline (manager node can be HUMAN or AGENT).
- Provide testable behavior in mock/dev environments and a manual system smoke path.

**Non-Goals:**
- Full daemonized agent lifecycle management (later milestones).
- IPC/form routing execution logic (M05+).
- Budget-gated model proxy integration (M09+).

## Decisions

### 1) Runtime launch backend (exploration)
- **Chosen for M04:** Direct subprocess launch with explicit user switch command template from configuration.
- **Rationale:** Fastest path to demonstrate restricted execution with minimal infra assumptions.
- **Rejected alternative A:** `systemd-run --uid` units per run; stronger service controls but higher host/environment variance (especially non-systemd dev hosts).
- **Rejected alternative B:** Dedicated privileged runtime daemon; cleaner long-term boundary but unnecessary complexity for M04 milestone proof.

### 2) Nullclaw command source
- **Chosen for M04:** Config-driven command template (env/settings) rather than hard-coded binary flags.
- **Rationale:** Nullclaw docs are evolving; config-first keeps implementation adaptable without code churn.
- **Rejected alternative:** Hard-code Nullclaw invocation now; likely rework after docs arrive.

### 3) Runtime path contract
- **Chosen for M04:** Use Nullclaw home structure per user account (`~/.nullclaw/config.json`, `~/.nullclaw/workspace`) as canonical runtime path inputs.
- **Rationale:** Aligns with upstream Nullclaw defaults and avoids dual-workspace drift.
- **Rejected alternative:** Continue using `/home/<user>/workspace` for runtime execution; mismatches Nullclaw runtime expectations.

### 4) Run metadata storage
- **Chosen for M04:** Filesystem metadata record in workspace runtime/journal area (JSON entry per run), with API response summary.
- **Rationale:** Avoids premature schema expansion while still preserving auditable run details.
- **Rejected alternative:** New DB run table in M04; stronger queryability but broader schema/API surface before workflow requirements are settled.

### 5) Runtime state storage for control-plane status
- **Chosen for M04:** Store current gateway running flag + latest start/stop timestamps on `nodes`.
- **Rationale:** Supports immediate on/off control visibility for operator and future delegated automation.
- **Rejected alternative:** Infer running state solely from PID file/process checks every request; simpler schema but weaker canonical-state tracking.

### 6) Output boundary enforcement
- **Chosen for M04:** Enforce `drafts`-bound output contract in runtime bootstrap checks and command working directory.
- **Rationale:** Aligns with PRD maker/checker model and M04 acceptance.
- **Rejected alternative:** Allow wide workspace writes in M04; faster but weakens safety posture.

### 7) Human workspace and line-management baseline
- **Chosen for M04:** Register existing kernel runner (for example `macos`) as HUMAN node with workspace under repo root (`<repo>/workspace/humans/<username>`), and require manager reference when provisioning AGENT nodes.
- **Rationale:** Establishes minimal company structure needed for next milestone message routing while keeping kernel/operator identity and workflow participation in one canonical DB model.
- **Rejected alternative:** Keep human actor outside canonical nodes and hierarchy; blocks formal approval/message routing parity with agent nodes.

## Risks / Trade-offs

- [Risk] Nullclaw CLI semantics may differ from initial template assumptions. -> Mitigation: command template config + follow-up alignment pass when user shares docs.
- [Risk] User-switch execution differs by host tools (`sudo`, `runuser`, etc.). -> Mitigation: adapterized command builder and explicit smoke script for system verification.
- [Risk] Parent directory permissions can block manager traversal into `~/.nullclaw/workspace`. -> Mitigation: apply permission policy to user home and `.nullclaw` parent path in addition to workspace tree.
- [Risk] File-based metadata is less queryable than DB records. -> Mitigation: stable metadata schema and planned promotion to relational records in later milestones if required.
- [Risk] DB running-state drift from real process state (crash/kill outside kernel). -> Mitigation: gateway status action reconciles PID checks and updates DB state.
- [Risk] Existing AGENT rows without manager violate new policy. -> Mitigation: add `set_line_manager` action and migration-time/operator remediation step for baseline nodes.

## Migration Plan

1. Add runtime module and configuration defaults in disabled-safe mode.
2. Add endpoint/service wiring and mock-compatible tests.
3. Run runtime smoke in local system environment with provisioned `agent_director_01`.
4. Register HUMAN baseline node (`macos`) with repo-local workspace and link `Director_01` line manager.
5. If smoke fails, rollback by disabling runtime endpoint path and keeping M03 provisioning intact.

## Open Questions

- Whether M04 should store run metadata only on filesystem or also in DB now.
- Whether per-run process timeout should be static or configurable by node/autonomy level.
- When to formalize agent prompt-definition standards and onboarding skill guidance (deferred by request to later milestone).
