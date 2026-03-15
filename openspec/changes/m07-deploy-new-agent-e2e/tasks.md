## 1. OpenSpec + Tracking Baseline

- [x] 1.1 Create and validate M07 OpenSpec artifacts for `m07-deploy-new-agent-e2e` (`proposal.md`, `design.md`, specs deltas, `tasks.md`).
- [x] 1.2 Update milestone trackers to make this the active change and rename M07 focus from generic `SPAWN_AGENT` wording to `deploy_new_agent` E2E validation.

## 2. IPC Routing Contract: stage_skill

- [x] 2.1 Update IPC router routed frontmatter generation to always write kernel-managed `stage_skill`.
- [x] 2.2 Ensure routed `stage_skill` equals next stage `required_skill` and terminal no-holder writes empty string.
- [x] 2.3 Add/adjust IPC integration tests to verify stage skill overwrite behavior and terminal empty value contract.

## 3. Workspace Form Skill Naming Migration (Hyphen Convention)

- [x] 3.1 Rename workspace form stage skill directories to hyphen style across `workspace/forms/*`.
- [x] 3.2 Update all affected `required_skill` values in workspace `workflow.json` definitions to match renamed folders.
- [x] 3.3 Update workflow-authoring examples/docs (master + reference skill docs) to hyphen stage skill naming.

## 4. Deploy Skill Hardening and Validation Assets

- [x] 4.1 Add director-seeded Nullclaw config template into `workspace/forms/deploy_new_agent/skills/deploy-new-claw-agent/` and reference it in stage skill SOP.
- [x] 4.2 Expand deploy stage SOP with live-smoke preflight guidance for auth sync and autonomy `full` setup for Director/HR/Ops participants.
- [x] 4.3 Add forms smoke script/runbook for full `deploy_new_agent` cycle (macos outbox seed, IPC scans, per-holder heartbeat prompt runs, archive/evidence checks).
- [x] 4.4 Add deterministic integration test that exercises full `deploy_new_agent` route cycle with holder transitions and archive closure.

## 5. Verification, Documentation, and Skill Delta Review

- [x] 5.1 Run `uv run pytest -q` and fix regressions.
- [x] 5.2 Run `openspec validate --type change m07-deploy-new-agent-e2e --strict` and fix any artifact/spec issues.
- [x] 5.3 Update `docs/current-task.md`, `docs/plan.md`, `docs/implement.md`, and `docs/documentation.md` for implemented M07 behavior and deferred `UPDATE_TEMPLATE` scope.
- [x] 5.4 Skill Delta Review Gate: update reusable IPC/deploy workflow skills and commands with new `stage_skill` contract and E2E smoke SOP.
