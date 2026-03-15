Active implementation change: `m10a-agentic-workflow-verification-surface`

Implementation focus

1. Close the remaining canonical workflow gaps identified in `docs/agentic-workflow-gap-analysis.md` and detailed in `docs/agentic-workflow-implementation-and-test-plan.md`.
2. Add canonical usage/session read APIs so session cost, token totals, and timing can be queried without direct DB access.
3. Add a kernel-mediated agent prompt invocation surface suitable for low-cost verification runs.
4. Add a canonical budget report surface for organization-wide before/after spend comparison.
5. Enrich active-agent discovery so operators and supervising agents can plan tests without repo-local config inspection.
6. Add endpoint-backed helper wrappers under `scripts/` and explicitly distinguish canonical wrappers from diagnostic-only utilities.
7. Package the final budget-consumption verification workflow as a reusable skill and complete the end-to-end validation using only supported endpoints/scripts.

Status

- M10 is archived as `openspec/changes/archive/2026-03-11-m10-waterfall-budget-engine`.
- M10a implementation is complete: discovery, budget reporting, runtime invocation, usage read APIs, wrapper scripts, and the mirrored verification SOP skill are in place.
- Deterministic mock-mode usage/spend persistence now makes the canonical proof path observable in approved low-cost verification environments.
- Validation passed:
  - `uv run pytest -q tests/test_usage_actions.py tests/test_runtime_actions.py tests/test_budgets_actions.py`
  - `uv run pytest -q`
  - `openspec validate --type change m10a-agentic-workflow-verification-surface --strict`
- Canonical wrapper-only end-to-end verification passed on 2026-03-11.
- New follow-up planning item: inspect and reduce the current Nanobot/OmniClaw coupling. The live usage path is currently implemented by customized Nanobot runtime code in `/home/macos/nanobot/nanobot/agent/loop.py` that directly imports `omniclaw.config`, `omniclaw.db.session`, and `omniclaw.db.repository` to auto-record LLM calls.
- Preferred direction for planning: move the customized Nanobot runtime under OmniClaw control (monorepo-owned copy/package strategy), preserve automatic runtime-level logging, and design a cleaner integration contract than direct repo import dependence from an external checkout.

Notes

- The target proof-path for this change is agent-usable and endpoint-backed; repo directory scans and direct SQLite reads may still help diagnosis but do not count as workflow completion.
- The validated sequence is: list agents, capture budget baseline, invoke cheap prompt, inspect usage summaries, capture post-run budget report, and compare deltas.
- Keep Skill Delta Review in scope throughout implementation so the final verification SOP is captured immediately once stable.
