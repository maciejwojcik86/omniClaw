## Why

M10 delivered the waterfall budget engine, but the current verification path is still too developer-oriented in several key places. The product can capture usage, manage budgets, and list runtime agents, yet the end-to-end workflow required for autonomous verification still depends on incomplete read/report surfaces, repo-local helper behavior, or developer-only inspection paths.

Before moving to the next milestone, OmniClaw needs confidence that the current implementation works as intended through canonical interfaces available to Nanobot agents themselves. This change closes the remaining control-plane gaps and packages the final workflow so operators and supervising agents can verify budget consumption without repository discovery, direct DB reads, or ad hoc runtime bootstrapping.

See supporting analysis and execution detail in:
- `docs/agentic-workflow-gap-analysis.md`
- `docs/agentic-workflow-implementation-and-test-plan.md`

## What Changes

- Add a canonical agent catalog surface that exposes active agents with richer runtime, provider, and budget metadata.
- Add a canonical organization/team budget report surface suitable for before/after spend comparison.
- Add a canonical kernel-mediated agent prompt invocation surface for low-cost verification runs.
- Add canonical usage/session summary read endpoints so session cost, token counts, and timing can be inspected without direct DB access.
- Add endpoint-backed helper scripts for the verification workflow and classify canonical wrappers versus developer diagnostics.
- Run and document the final end-to-end budget verification workflow for the current milestone using only supported endpoints/scripts.

## Capabilities

### New Capabilities
- `agentic-workflow-verification-surface`: Canonical discovery, invocation, usage reporting, and report-wrapper surfaces for autonomous budget verification.

### Modified Capabilities
- `budget-management`: Add stable read/report responses for organization-wide budget inspection and comparison-friendly summaries.
- `usage-logging`: Add query/report endpoints for session and node usage summaries.
- `agent-runtime-bootstrap`: Add a kernel-mediated prompt execution surface for delegated agent verification runs.
- `litellm-integration`: Expose provider/model metadata needed by canonical verification reporting.

## Impact

- FastAPI API surface: new read endpoints and/or actions for agents, budgets, runtime invocation, and usage summaries.
- Scripts: new canonical wrappers under `scripts/runtime/`, `scripts/budgets/`, and `scripts/usage/`, plus classification of diagnostic-only helpers.
- Docs: update implementation, documentation, plan/current-task, and add final verification runbook references.
- Skills: capture the final verification workflow as a reusable skill and refresh related operational skills.
