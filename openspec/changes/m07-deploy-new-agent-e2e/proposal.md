## Why

M06 delivered generic form routing and deterministic state transitions, but deployment-oriented workflow execution still depends on manual operator interpretation and lacks an explicit routed frontmatter cue for which stage skill to run next. The current `deploy_new_agent` workflow also mixes underscore and hyphen naming in stage skill identifiers, and operators need a repeatable end-to-end smoke path that validates real host participants and stage handoffs.

This change hardens the `deploy_new_agent` form cycle for M07 by making routed guidance explicit (`stage_skill`), standardizing workspace-form skill naming to hyphen style, and adding deterministic + live-smoke verification assets.

## What Changes

- Add kernel-managed routed frontmatter field `stage_skill` in IPC routing.
  - Value equals the next stage `required_skill`.
  - Terminal/no-holder stage routes with `stage_skill: ""`.
  - Incoming stale `stage_skill` values are overwritten by kernel on every hop.
- Keep deployment execution model manual-at-stage:
  - `AGENT_DEPLOYMENT` is executed by the holder using `deploy-new-claw-agent` skill.
  - Kernel archives when stage decision reaches terminal stage with `target: null`.
- Standardize workspace form stage-skill naming to hyphen case across `workspace/forms/*`.
  - Keep form type keys snake_case (for example `deploy_new_agent`, `message`).
- Harden `deploy-new-claw-agent` stage skill package:
  - add seeded config template copied from Director runtime config,
  - document auth sync and autonomy `full` preflight for live smoke participants.
- Add deterministic integration coverage for full `deploy_new_agent` IPC stage progression and `stage_skill` routing contract.
- Add operator smoke script for host E2E cycle:
  - seed request in `workspace/macos/outbox/send`,
  - run IPC scans between holders,
  - run holder agents one-by-one via heartbeat prompt,
  - verify archive + deployment evidence.

In scope:
- `deploy_new_agent` full-cycle routing reliability.
- `stage_skill` routed frontmatter metadata.
- Workspace form skill naming migration (hyphen style).
- Deploy-skill runbook/template hardening.
- Automated tests + live smoke script/runbook.

Out of scope:
- `UPDATE_TEMPLATE` workflow and endpoint changes (deferred).
- Kernel-side auto-provision side effects triggered at approval transition.
- New authorization policy for stage-skill package execution.

## Capabilities

### New Capabilities
- `deploy-new-agent-e2e`: deterministic and host-runbook validation path for full `deploy_new_agent` workflow handoff and closure.

### Modified Capabilities
- `file-ipc-router`: routed-form frontmatter contract includes kernel-managed `stage_skill`.

## Impact

Affected code and systems:
- `src/omniclaw/ipc/service.py` routed frontmatter generation.
- `tests/test_ipc_actions.py` routing contract + full-cycle deploy workflow integration coverage.
- `workspace/forms/*` workflow required-skill naming and skill folder naming.
- `workspace/forms/deploy_new_agent/skills/deploy-new-claw-agent/*` SOP/template package.
- `scripts/forms/*` host smoke tooling for staged deploy workflow validation.
- `docs/*` trackers and operator documentation for M07 behavior.
