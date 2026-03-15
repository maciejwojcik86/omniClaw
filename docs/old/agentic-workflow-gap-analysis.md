# Agentic Workflow Gap Analysis

## Purpose

This report reviews the current OmniClaw operator/runtime surface against a stricter requirement:

> Any workflow we expect Nanobot agents to execute autonomously later should be available through canonical kernel endpoints and/or packaged helper scripts, without depending on repository structure knowledge, direct database reads, or developer-only shell improvisation.

The specific scenario evaluated here is the desired budget-verification workflow:

1. Discover all active agents.
2. Obtain a current budget/allowance summary for the organization and each agent.
3. Invoke each agent with a small prompt.
4. Inspect usage/session/cost summaries for those runs.
5. Re-run budget reporting and verify that spend increased and remaining budget decreased.

This report identifies what already exists, what is only partially canonical, what is missing, why each gap matters, and what should be introduced next.

---

## Executive Summary

OmniClaw already has a meaningful canonical control surface for agentic operations:

- runtime action endpoint with `list_agents`
- budget action endpoint with waterfall-management operations
- session export endpoint
- several packaged helper scripts under `scripts/`

However, the current workflow is not yet fully agent-verifiable end to end.

The main issue is that several operator checks still depend on one of the following:

- repo-local helper scripts that read database files directly
- repo-local runtime invocation wrappers that assume source-tree access
- incomplete read/report APIs for usage and budget summaries
- sparse discovery metadata for active agents

As a result, a human developer can validate the system today, but an autonomous Nanobot agent constrained to approved endpoints/scripts cannot yet perform the full scenario cleanly without hidden assumptions.

### Most important gaps

1. **No canonical rich agent catalog/report surface**
   - `list_agents` exists, but likely lacks the full metadata needed for planning and validation.

2. **No clearly canonical all-agent budget report endpoint**
   - budget mutations and partial views exist, but there is not yet a dedicated, endpoint-backed, stable report for organization-wide allowance/spend inspection.

3. **No canonical kernel-level agent invocation endpoint**
   - `scripts/runtime/run_agent.sh` is useful for developers/operators, but it is not the right autonomous interface for a Nanobot agent.

4. **No canonical usage/session summary read endpoints**
   - usage data is being captured, but reporting currently depends too much on local DB access or export-only workflows.

5. **Current helper scripts are uneven in canonicality**
   - some are good endpoint wrappers, while others are local inspection tools packaged as scripts.

### Recommendation priority

Highest-priority product additions should be:

1. a canonical agent catalog endpoint/script
2. a canonical budget summary/report endpoint/script
3. a canonical invoke-agent endpoint/script
4. canonical usage/session summary endpoints/scripts

These four additions would turn the current workflow from “developer-operable” into “agent-operable”.

---

## Scope And Evaluation Standard

This report evaluates each workflow step using the following standard.

A workflow step is considered **canonical and agent-verifiable** when:

- it is available through a kernel endpoint and/or a packaged helper script in `scripts/`
- the helper script acts as a thin wrapper over stable endpoint/runtime contracts
- it does not require repository structure discovery
- it does not require direct DB file access
- it does not require manual developer intervention to bypass missing permissions or missing features

A workflow step is considered **non-canonical** when it depends on:

- scanning repo directories to discover state
- directly reading SQLite files as the primary interface
- relying on local source-tree execution assumptions unavailable to normal agents
- developer-only shell exploration used as the workflow itself rather than as diagnosis

---

## Desired End-To-End Workflow

The target workflow under review is:

1. discover all active agents and their roles/descriptions
2. retrieve a current budget and allowance summary
3. call each agent with a cheap prompt
4. retrieve per-session or per-agent usage/cost summaries
5. retrieve budget summary again and compare deltas

This workflow should ideally be executable by:

- a human operator using approved scripts/endpoints
- a supervising Nanobot agent using the same approved scripts/endpoints

That is the standard used for the findings below.

---

## Findings

## Finding 1 — Active agent discovery exists, but metadata is probably too thin

### Current state

OmniClaw already exposes a canonical runtime control surface:

- `POST /v1/runtime/actions`
- packaged helper: `scripts/runtime/trigger_runtime_action.sh`
- supported action includes: `list_agents`

This is a strong foundation because it avoids the need to scan directories such as `workspace/agents/` just to know what agents exist.

### Why this is good

This already satisfies an important part of the agent-verifiability requirement:

- discovery is kernel-mediated
- operators and future agents can call the same supported path
- repo structure does not need to be treated as an API

### Gap

The likely limitation is not existence, but completeness of the returned metadata.

For the workflow you want, a simple list of names/IDs is not enough. The caller should also be able to learn:

- whether the node is active
- type/role
- human-readable description
- parent/manager relationship
- whether runtime is available
- provider/model summary
- whether a virtual API key is configured
- budget mode and possibly current budget status

If `list_agents` only returns a minimal runtime inventory, then a second or third call is needed to assemble a usable working picture.

### Why this matters

A supervising agent should not have to reconstruct basic organizational metadata by calling multiple unrelated APIs or by inferring state from config files.

If discovery is too thin:

- workflow planning becomes brittle
- scripts need custom joins/logic
- operators and agents get inconsistent views
- future autonomous orchestration becomes more error-prone

### Recommendation

Keep `list_agents`, but enrich it or add a dedicated catalog endpoint such as:

- `GET /v1/agents`
- or `GET /v1/agents/catalog`

Recommended fields:

- `node_id`
- `name`
- `type`
- `status`
- `role_name`
- `description`
- `manager_node_id` / `manager_name`
- `gateway_running`
- `provider`
- `model`
- `has_virtual_api_key`
- `budget_mode`
- `effective_daily_limit_usd`
- `current_spend_usd`
- `remaining_budget_usd`

### Severity

**Medium** — the surface exists, but likely needs enrichment to support autonomous workflow planning.

---

## Finding 2 — Budget control actions exist, but canonical reporting is incomplete

### Current state

OmniClaw exposes budget operations through:

- `POST /v1/budgets/actions`

Documented actions include:

- `sync_all_costs`
- `sync_node_cost`
- `update_node_allowance`
- `team_budget_view`
- `set_team_allocations`
- `set_node_budget_mode`
- `run_budget_cycle`
- `recalculate_subtree`

There is also a local report helper:

- `scripts/budgets/generate_budget_report.py`

### What is working well

The budget engine itself appears to be modeled properly around canonical DB state:

- `budgets`
- `budget_allocations`
- `budget_cycles`

There is already an endpoint-backed action model for budget operations, which is good for automation.

### Gap

The main gap is that there is not yet a clearly designated, endpoint-backed, read-only **organization budget report** surface suitable for autonomous inspection.

`team_budget_view` may partially satisfy this, but the current operator tooling suggests a remaining reliance on local report assembly. The helper script `generate_budget_report.py` appears to do repo-local reads and formatting instead of acting purely as an endpoint wrapper.

That makes it less suitable as the canonical interface for future Nanobot self-service.

### Why this matters

Your intended workflow starts and ends with budget reporting. If the “report” path is not cleanly canonical, then:

- comparisons are harder to automate
- output shape may not be stable
- agents may need unauthorized DB access
- the report path may diverge from the officially supported control plane

A real autonomous workflow needs one stable budget-report contract that says, in effect:

- here is the company budget state
- here is the manager/child allocation state
- here is each agent’s current spend and remaining budget
- here is the current reconciliation/sync status

### Recommendation

Introduce a dedicated budget report endpoint, for example:

- `GET /v1/budgets/report`
- or new budget action `company_budget_report`

Recommended response content:

- company/root totals
- cycle date / last sync metadata
- per-node budget summary
- manager → child allocations
- budget mode per node
- effective cap / daily inflow
- current spend
- remaining allowance
- rollover reserve
- provider sync status and any sync errors

Then either:

- replace `generate_budget_report.py` with an endpoint-only wrapper, or
- add a new canonical script such as `scripts/budgets/get_budget_report.sh`

### Severity

**High** — the budget engine exists, but the reporting surface should be promoted to a first-class canonical API for agentic verification.

---

## Finding 3 — Agent invocation is available for developers/operators, but not yet canonically exposed for autonomous agents

### Current state

There is a useful operator helper:

- `scripts/runtime/run_agent.sh --agent-name <name> --message <text> [--session-key <key>]`

This appears to run a repo-local Nanobot agent with the correct environment so usage logging works.

### What is good about it

This is practical for manual testing and developer operations.

It helps verify:

- agent runtime configuration
- provider routing
- usage logging integration
- session key propagation

### Gap

This helper is not yet a proper autonomous interface for other agents.

Reasons:

- it assumes repo-local source/runtime access
- it depends on shell environment and path setup
- it appears to be a direct runtime wrapper rather than a kernel-mediated action
- a restricted Nanobot agent should not have to know how to bootstrap another agent’s repo-local execution environment

### Why this matters

If autonomous supervisory agents are expected to run test prompts against subordinate agents, then invocation itself should be a supported control-plane operation.

Without that, the system is effectively saying:

- discovery and budget state are kernel-managed
- but actual execution still requires developer-style local runtime knowledge

That breaks the “single canonical workflow” principle.

### Recommendation

Introduce a canonical execution surface, such as:

- `POST /v1/agents/run`
- or `POST /v1/runtime/actions` with action `run_agent_prompt`

Suggested request:

```json
{
  "node_name": "Director_01",
  "session_key": "manual-test-director-001",
  "message": "Write one short sentence about teamwork."
}
```

Suggested response:

- `status`
- `node_id`
- `node_name`
- `session_key`
- `response_text`
- `run_id` or correlation ID
- `provider/model metadata`
- `started_at` / `completed_at`

Then provide a packaged helper script that only wraps that endpoint.

### Severity

**High** — this is one of the most important gaps for turning the current workflow into a truly agent-operable flow.

---

## Finding 4 — Usage is captured, but canonical usage-reading/reporting is missing

### Current state

Usage/session tracking was implemented previously and the documentation confirms:

- token/cost/timing data is captured into canonical persistence
- session export is available through `POST /v1/sessions/export`
- helper script exists: `scripts/budgets/show_session_cost.py`

### What is good

The underlying data pipeline appears to exist. This is a major strength:

- usage data is being captured centrally
- export is already a supported endpoint
- the system has enough raw data to support robust reporting

### Gap

There does not appear to be a first-class read API for usage summaries.

The current helper script `show_session_cost.py` appears to act as a local DB reader rather than an endpoint-only wrapper. That means the canonical runtime captures usage, but canonical consumers cannot yet query it cleanly through the kernel.

Missing capabilities likely include:

- get usage summary by `session_key`
- get usage summary by `node_name` / `node_id`
- list recent sessions for a node
- list recent LLM calls
- return aggregate session duration/span, token totals, and USD cost in a stable JSON shape

### Why this matters

Your workflow explicitly requires checking:

- whether the test session ran
- how long the session lasted
- what the token/cost footprint was

If the only way to answer that is by direct SQLite access, then the product is not yet exposing its own canonical telemetry surface.

That is a critical gap for agent autonomy because future agents should be able to inspect cost and usage through approved APIs, not through DB internals.

### Recommendation

Add usage-reporting read endpoints such as:

- `GET /v1/usage/sessions/{session_key}/summary`
- `GET /v1/usage/nodes/{node_id}/recent-sessions`
- `GET /v1/usage/nodes/{node_id}/summary`
- `GET /v1/usage/llm-calls?node_name=...&session_key=...`

Suggested summary fields:

- `node_id`
- `node_name`
- `session_key`
- `llm_call_count`
- `prompt_tokens`
- `completion_tokens`
- `reasoning_tokens`
- `total_tokens`
- `cost_usd`
- `first_call_at`
- `last_call_at`
- `session_span_seconds`
- optional model/provider rollup

Then convert `show_session_cost.py` into a wrapper over those endpoints or replace it with canonical scripts under a dedicated `scripts/usage/` area.

### Severity

**High** — usage capture exists, but the lack of canonical read APIs blocks autonomous validation and reporting.

---

## Finding 5 — Session export exists and is appropriately canonical, but it is not enough by itself

### Current state

Session export is available through:

- `POST /v1/sessions/export`

This is already a good pattern because it exposes transcript extraction as a supported endpoint rather than forcing callers to know file paths.

### Why this is good

This aligns well with the desired design philosophy:

- kernel owns the contract
- callers do not need to know internal storage layout
- export metadata can be tracked centrally

### Gap

Export is useful, but it is not a substitute for usage reporting.

An exported transcript tells you what happened conversationally, but it does not necessarily provide a concise, structured answer to questions like:

- how much did this session cost?
- how many tokens did it use?
- what was the active session span?
- how many model calls were made?

### Why this matters

Without a separate usage-summary API, operators and agents may misuse transcript export as a pseudo-reporting tool. That increases complexity and makes budget verification workflows slower and less deterministic.

### Recommendation

Keep `POST /v1/sessions/export`, but treat it as complementary.

It should be paired with usage-summary endpoints so that callers can choose between:

- transcript retrieval
- concise cost/usage reporting

Optional improvements:

- endpoint to list previous exports
- endpoint to fetch export metadata by session/node
- script wrapper such as `scripts/usage/export_session.sh`

### Severity

**Low to Medium** — export is in good shape, but it should be complemented by summary/report endpoints.

---

## Finding 6 — Current helper scripts are mixed: some are canonical wrappers, some are local inspection tools

### Current state

The `scripts/` directory already contains several useful helpers, including:

- runtime action trigger helpers
- budget action trigger helpers
- session cost helper
- local budget report helper

### Problem

Not all scripts are equal in architectural quality.

Some scripts are ideal for long-term agentic use because they:

- call a stable kernel endpoint
- wrap a supported action
- avoid local DB or repo-layout assumptions

Others are convenient local tools, but they are not truly canonical because they:

- read SQLite directly
- inspect local config files
- assume repo checkout access
- implicitly act as developer utilities rather than product interfaces

### Why this matters

If these two classes of scripts are not distinguished clearly, then teams can mistakenly treat a local diagnostic tool as proof that the product supports autonomous operation.

That creates false confidence and hides missing kernel interfaces.

### Recommendation

Classify scripts into two categories explicitly:

1. **canonical agent-usable wrappers**
   - endpoint-backed
   - stable arguments
   - no direct DB reads
   - safe for future autonomous use

2. **developer/operator diagnostics**
   - may read repo-local files or DB directly
   - useful for debugging
   - not acceptable as the proof-path for autonomous workflows

Recommended follow-up:

- rename or reorganize scripts if needed
- add headers/comments stating whether a script is canonical or diagnostic
- prefer creating endpoint-backed wrappers before adding new diagnostic-only scripts

### Severity

**Medium** — this is a governance/tooling clarity gap that can distort validation outcomes.

---

## Finding 7 — The current manual verification path still relies too much on local DB access for reporting

### Current state

The current practical testing path for cost/session review appears to rely on helper scripts that read the local SQLite DB.

### Problem

This violates the intended long-term product model for autonomous agents:

- Nanobot agents should not need filesystem-level DB access
- database schema should remain an implementation detail behind the kernel
- reporting should be queryable through stable API contracts

### Why this matters

Direct DB reads are tempting because they are fast and convenient for developers. However, they create several problems:

- tight coupling to schema details
- incompatibility with restricted agent environments
- brittle workflows across migration changes
- hidden difference between human debug paths and agent execution paths

### Recommendation

Treat all direct-DB scripts for reporting as temporary developer tools. Replace them over time with:

- kernel-backed read endpoints
- endpoint-only helper scripts
- stable machine-readable output formats for automation

### Severity

**High** — this is a core productization gap for autonomous operations.

---

## Finding 8 — The workflow lacks a single canonical “test runbook” script composition for future agents

### Current state

Pieces of the workflow exist, but they are spread across multiple helpers and not yet packaged as one canonical agent-usable verification routine.

### Problem

Even if all low-level endpoints existed, future agents would still benefit from a packaged SOP/script set that defines the official sequence:

1. list active agents
2. fetch budget baseline
3. invoke one or more agents
4. fetch usage summaries
5. fetch budget summary again
6. compare and report deltas

Without this packaging, each agent or operator may reinvent orchestration logic.

### Why this matters

Autonomous systems need not just APIs, but also repeatable operational workflows.

A stable runbook/script composition helps with:

- reproducibility
- comparability of results
- simpler debugging
- smaller agent prompt burden
- better future skill packaging

### Recommendation

Once the missing APIs are added, create a focused skill and script bundle for the scenario, for example:

- `.codex/skills/verify-budget-consumption-flow/SKILL.md`
- `scripts/runtime/list_agents.sh`
- `scripts/budgets/get_budget_report.sh`
- `scripts/runtime/run_agent_prompt.sh`
- `scripts/usage/get_session_usage.sh`
- `scripts/budgets/compare_budget_reports.py`

### Severity

**Medium** — orchestration packaging should follow the endpoint additions.

---

## Recommended Canonical Surface Additions

## 1. Agent catalog endpoint/script

### Proposed endpoint
- `GET /v1/agents`
- or `GET /v1/agents/catalog`

### Purpose
Return all active agents with enough metadata for planning and monitoring.

### Minimum fields
- node id/name/type/status
- role/description
- manager relationship
- runtime availability
- provider/model summary
- key presence
- budget summary preview

### Script
- `scripts/runtime/list_agents.sh`

### Why it should exist
This becomes the one approved discovery path for operators and agents.

---

## 2. Budget summary/report endpoint/script

### Proposed endpoint
- `GET /v1/budgets/report`
- or budget action `company_budget_report`

### Purpose
Return organization-wide budget state in a structured format suitable for before/after comparisons.

### Minimum fields
- company totals
- cycle metadata
- per-node allowance/spend/remaining
- allocations and manager tree
- sync errors/status

### Script
- `scripts/budgets/get_budget_report.sh`

### Why it should exist
This is the canonical answer to “what is the current allowance/budget state?”.

---

## 3. Agent prompt execution endpoint/script

### Proposed endpoint
- `POST /v1/agents/run`
- or runtime action `run_agent_prompt`

### Purpose
Allow a supervising caller to trigger a simple test prompt against a target agent through the kernel contract.

### Minimum fields
- target node
- session key
- message
- run status
- response text
- correlation/run id

### Script
- `scripts/runtime/run_agent_prompt.sh`

### Why it should exist
This removes the need for repo-local runtime wrappers as the canonical execution path.

---

## 4. Usage/session summary endpoints/scripts

### Proposed endpoints
- `GET /v1/usage/sessions/{session_key}/summary`
- `GET /v1/usage/nodes/{node_id}/recent-sessions`
- `GET /v1/usage/nodes/{node_id}/summary`

### Purpose
Expose captured usage data in a queryable control-plane format.

### Minimum fields
- session key
- node
- call count
- tokens by type
- cost
- timestamps
- session span/duration

### Scripts
- `scripts/usage/get_session_usage.sh`
- `scripts/usage/list_recent_sessions.sh`

### Why they should exist
These are the canonical answer to “did the run happen, how long was it, and what did it cost?”.

---

## 5. Endpoint-only report wrappers and script classification

### Proposed improvement
Review `scripts/` and explicitly classify each helper as either:

- canonical endpoint-backed wrapper
- diagnostic/developer-only tool

### Why it should exist
This prevents local inspection tools from being mistaken for product interfaces.

---

## Prioritized Backlog Recommendation

## Priority 1 — unblock full autonomous verification

1. Add canonical usage/session summary endpoints.
2. Add canonical agent invocation endpoint.
3. Add canonical budget report endpoint.
4. Add endpoint-backed script wrappers for the above.

### Why this is first
These items directly unlock the exact workflow under test.

---

## Priority 2 — improve discoverability and script discipline

5. Enrich agent discovery into a full catalog response.
6. Add script classification conventions and documentation.
7. Convert current local report helpers to endpoint-backed wrappers where possible.

### Why this is second
These items reduce ambiguity and improve autonomous operability, but they depend less critically on core missing functionality.

---

## Priority 3 — package the full verification workflow as a skill/runbook

8. Create a dedicated verification skill for budget-consumption testing.
9. Add a composed runbook/script set for before/after budget validation.
10. Ensure output is machine-readable for autonomous comparison.

### Why this is third
This is the right closure step once the control-plane surface is complete.

---

## Practical Interpretation For Current Testing

At the moment, OmniClaw is in a mixed state:

- **developer/operator validation is possible today**
- **fully canonical autonomous validation is not yet complete**

That means the correct testing stance is:

- use existing endpoint-backed scripts whenever available
- treat repo-local DB reads and repo-layout discovery only as temporary diagnostics
- record every place where a workflow step still lacks a canonical endpoint/script
- do not count developer-only workarounds as proof that the agentic system is complete

This is especially important for the budget-verification workflow because it is one of the strongest demonstrations of whether the system is actually agent-operable rather than only developer-operable.

---

## Conclusion

OmniClaw already has the foundations needed to support agent-verifiable budget workflows:

- canonical runtime actions
- canonical budget action surface
- canonical session export
- canonical persisted usage and budget state

The remaining work is not the absence of a budgeting system, but the absence of a fully rounded **agent-facing control plane** for discovery, invocation, usage reporting, and structured before/after comparison.

In short:

- the underlying system is substantially implemented
- the canonical autonomous workflow surface is not yet complete
- the biggest missing pieces are **usage read APIs**, **kernel-mediated agent invocation**, and a **first-class budget reporting endpoint**

Once those are added and wrapped in approved scripts, the workflow you described can become a genuine agent-run self-test rather than a developer-assisted validation.
