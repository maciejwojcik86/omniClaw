# Agentic Workflow Implementation And Test Plan

## Purpose

This document turns the gap analysis into an execution plan that can be delegated to other agents.

It is intentionally structured in two phases:

1. **Fill the canonical workflow gaps first** so the target workflow becomes genuinely agent-operable.
2. **Run the end-to-end budget verification workflow second** using only approved endpoints and packaged scripts.

This document is designed to answer three questions clearly:

- what needs to be implemented or upgraded first
- what exact endpoints/scripts should exist when the work is complete
- how another agent should run the workflow step by step once the control plane is ready

This document complements, and should be read together with:

- `docs/agentic-workflow-gap-analysis.md`

---

## Guiding Principle

The target standard is not merely that a developer can complete the workflow using local shell access. The target standard is:

> A Nanobot agent with access only to approved kernel endpoints and packaged helper scripts should be able to execute the workflow without depending on repository structure knowledge, direct database access, or hidden manual intervention.

This means that during implementation and validation:

- endpoint-backed scripts are preferred over local DB readers
- stable API contracts are preferred over repo-layout discovery
- missing permissions or missing endpoints are treated as product gaps
- human workarounds must not be mistaken for proof of autonomous capability

---

## Target Workflow To Enable

The workflow we want to support canonically is:

1. discover all active agents and their roles/descriptions
2. fetch an organization-wide budget summary
3. call each target agent with a cheap prompt
4. inspect usage/session/cost summaries for those calls
5. fetch the budget summary again
6. compare before/after results and confirm spend propagation through the budget system

This should eventually be executable by:

- a human operator using packaged scripts
- a supervising agent using the same scripts/endpoints

---

## Current State Summary

At the time of writing:

### Already available or partially available
- runtime action endpoint with `list_agents`
- budget action endpoint with waterfall-management operations
- session export endpoint
- local runtime helper `scripts/runtime/run_agent.sh`
- local budget report helper `scripts/budgets/generate_budget_report.py`
- local usage helper `scripts/budgets/show_session_cost.py`

### Not yet complete as canonical agent workflow
- rich agent discovery metadata is incomplete or uncertain
- no first-class all-agent budget report endpoint is defined
- no kernel-mediated agent prompt execution endpoint is defined
- no first-class usage/session summary read endpoints are defined
- current helper scripts are mixed between canonical wrappers and local diagnostics

The rest of this document focuses on how to close those gaps.

---

## Phase 1 — Fill The Gaps First

## Objective

Create the minimum canonical control-plane surface required to support autonomous budget-verification testing.

## Success Criteria

Phase 1 is complete only when all of the following are true:

- active agents can be discovered through a stable endpoint/script with rich metadata
- current budget state can be retrieved through a stable endpoint/script without direct DB access
- a target agent can be invoked through a kernel-mediated endpoint/script
- usage and session summaries can be queried through stable endpoints/scripts
- all packaged scripts used by the workflow are clearly marked as canonical wrappers, not local diagnostics

---

## Workstream A — Canonical Agent Discovery

## Problem

A simple `list_agents` action exists, but autonomous workflow planning requires richer metadata than a minimal inventory usually provides.

## Goal

Provide one approved way to discover all active agents and enough metadata to decide what to test and how to interpret the results.

## Required Product Additions

### Preferred endpoint
- `GET /v1/agents`
- or `GET /v1/agents/catalog`

### Acceptable alternative
- enrich `POST /v1/runtime/actions` with action `list_agents` so it returns the same information

### Required response fields
Each agent record should include at least:

- `node_id`
- `name`
- `type`
- `status`
- `role_name`
- `description`
- `manager_node_id`
- `manager_name`
- `gateway_running`
- `provider`
- `model`
- `has_virtual_api_key`
- `budget_mode`
- `effective_daily_limit_usd`
- `current_spend_usd`
- `remaining_budget_usd`

### Required script wrapper
- `scripts/runtime/list_agents.sh`

### Script requirements
The script should:

- call the canonical endpoint only
- support both human-readable output and machine-readable JSON
- avoid reading local config files directly
- avoid scanning `workspace/agents/`

## Why this workstream matters

Without this, every future workflow will begin with reconstruction and guesswork. Discovery should be a first-class product capability, not a developer habit.

## Recommended delegation scope
A dedicated agent can own this workstream if assigned:

- endpoint design
- response schema
- route/service implementation
- wrapper script
- tests for inventory completeness and response shape

---

## Workstream B — Canonical Budget Summary Reporting

## Problem

Budget mutation and management actions exist, but the workflow needs a stable, read-only report surface for organization-wide before/after comparisons.

## Goal

Provide one canonical answer to the question:

> What is the current budget state of the company, managers, and agents?

## Required Product Additions

### Preferred endpoint
- `GET /v1/budgets/report`

### Acceptable alternative
- new budget action `company_budget_report`

### Required response sections
The response should include:

#### Top-level report metadata
- `generated_at`
- `cycle_date`
- `last_sync_at`
- `root_allocator_node`
- `sync_errors`

#### Company/root summary
- `daily_company_budget_usd`
- `current_total_spend_usd`
- `remaining_company_budget_usd`
- `controlled_budget_total_usd`
- `free_mode_nodes_total_usd` if relevant

#### Per-node summary
For each node:
- `node_id`
- `node_name`
- `manager_node_id`
- `budget_mode`
- `fresh_daily_inflow_usd`
- `effective_daily_limit_usd`
- `current_spend_usd`
- `remaining_budget_usd`
- `rollover_reserve_usd`
- `review_required_at`
- `provider_sync_status`
- `provider_sync_error` if any

#### Allocation view
- manager → child allocation percentages
- subtree totals where appropriate

### Required script wrapper
- `scripts/budgets/get_budget_report.sh`

### Script requirements
The script should:

- call only the canonical report endpoint
- optionally support `--json`
- optionally support `--sync-first` if reconciliation is a separate required action
- not read DB files directly

## Why this workstream matters

This workflow begins and ends with budget inspection. If reporting is not canonical, the full test is not canonical.

## Recommended delegation scope
A dedicated agent can own:

- response schema design
- route/service implementation
- integration with current budget engine state
- script wrapper
- tests for organization-wide report correctness

---

## Workstream C — Canonical Agent Prompt Invocation

## Problem

Current manual invocation depends on a repo-local runtime wrapper. That is good for developers, but it is not yet a stable control-plane operation for autonomous agents.

## Goal

Provide one approved way to send a simple prompt to a target agent and receive a structured response.

## Required Product Additions

### Preferred endpoint
- `POST /v1/agents/run`

### Acceptable alternative
- `POST /v1/runtime/actions` with action `run_agent_prompt`

### Required request fields
- `node_id` or `node_name`
- `message`
- `session_key`
- optional `timeout_seconds`
- optional `metadata`

### Required response fields
- `status`
- `node_id`
- `node_name`
- `session_key`
- `run_id`
- `response_text`
- `provider`
- `model`
- `started_at`
- `completed_at`
- optional `error`

### Required script wrapper
- `scripts/runtime/run_agent_prompt.sh`

### Script requirements
The script should:

- call only the canonical runtime endpoint
- expose stable flags like `--agent-name`, `--session-key`, `--message`
- avoid direct runtime bootstrapping knowledge in the caller
- return both friendly text and machine-readable JSON modes

## Why this workstream matters

This is the heart of the workflow. Without a canonical invoke-agent contract, the system still depends on developer runtime knowledge.

## Recommended delegation scope
A dedicated agent can own:

- endpoint contract
- service integration with runtime launch/call path
- script wrapper
- tests for successful run, invalid agent, and provider/config errors

---

## Workstream D — Canonical Usage And Session Summary APIs

## Problem

Usage capture exists, but autonomous consumers still lack a first-class telemetry-reading surface.

## Goal

Allow operators and agents to ask:

- did this session run?
- how many calls/tokens were used?
- how much did it cost?
- how long did it run?

without direct DB access.

## Required Product Additions

### Required endpoints
At minimum:

- `GET /v1/usage/sessions/{session_key}/summary`
- `GET /v1/usage/nodes/{node_id}/recent-sessions`
- `GET /v1/usage/nodes/{node_id}/summary`

### Recommended additional endpoint
- `GET /v1/usage/llm-calls`
  - filters: `node_id`, `node_name`, `session_key`, `limit`, `since`

### Required summary fields
For session summary:
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
- `provider_breakdown`
- `model_breakdown`

For node recent sessions:
- `session_key`
- `started_at`
- `ended_at`
- `llm_call_count`
- `cost_usd`
- `status`

### Required scripts
- `scripts/usage/get_session_usage.sh`
- `scripts/usage/list_recent_sessions.sh`

### Script requirements
The scripts should:

- call only usage endpoints
- support both friendly and machine-readable output
- not read SQLite directly
- be usable by other Nanobot agents without repo knowledge

## Why this workstream matters

This workstream is essential for verifying that the budget system is responding to real usage rather than only static configuration.

## Recommended delegation scope
A dedicated agent can own:

- new routes and schemas
- usage service query methods
- wrapper scripts
- tests for session summaries and recent-session listings

---

## Workstream E — Script Classification And Packaging Discipline

## Problem

Current scripts mix canonical wrappers and local diagnostics.

## Goal

Make it obvious which scripts are allowed for autonomous workflows and which are developer-only diagnostic tools.

## Required Product Additions

### Classification policy
Each script should be marked as one of:

1. **canonical wrapper**
2. **developer diagnostic**

### Recommended implementation options
- top-of-file comment header
- naming convention
- documentation table in `docs/documentation.md`
- directory split if useful

### Required behavior for canonical wrappers
- endpoint-backed or explicitly stable runtime contract
- no direct DB reads
- no repo-layout assumptions
- stable CLI arguments
- JSON output mode available where appropriate

## Why this workstream matters

This prevents accidental misuse of local developer utilities as proof that the system is agent-ready.

## Recommended delegation scope
A dedicated agent can own:

- script inventory
- classification policy
- per-script annotations
- documentation updates

---

## Workstream F — Canonical Verification Skill And Runbook

## Problem

Even after the APIs exist, the workflow still needs to be packaged into a repeatable operational SOP.

## Goal

Package the final verification flow into a skill and supporting helper scripts so it can be delegated repeatedly.

## Required Product Additions

### Proposed skill
- `.codex/skills/verify-budget-consumption-flow/SKILL.md`
- mirrored under `skills/verify-budget-consumption-flow/SKILL.md` if that remains the distribution convention

### Proposed helper scripts
- `scripts/runtime/list_agents.sh`
- `scripts/budgets/get_budget_report.sh`
- `scripts/runtime/run_agent_prompt.sh`
- `scripts/usage/get_session_usage.sh`
- `scripts/usage/list_recent_sessions.sh`
- `scripts/budgets/compare_budget_reports.py`

### Skill contents
The skill should include:

- scope
- required inputs
- preconditions
- exact execution sequence
- verification expectations
- failure interpretation guide
- fallback path for partial outages

## Why this workstream matters

The final goal is not just APIs, but repeatable delegated operations.

## Recommended delegation scope
This should be owned after the API surface is complete.

---

## Phase 1 Implementation Order

The recommended implementation sequence is:

1. **Usage/session read APIs**
2. **Agent prompt invocation endpoint**
3. **Budget report endpoint**
4. **Agent catalog enrichment**
5. **Canonical wrapper scripts for all of the above**
6. **Script classification pass**
7. **Verification skill/runbook packaging**

## Why this order

### 1. Usage APIs first
The system already captures usage, so exposing read access gives immediate leverage and makes later tests measurable.

### 2. Invocation endpoint second
Once sessions can be measured canonically, agent invocation can be tested as a proper control-plane feature.

### 3. Budget report third
Budget comparison becomes much more meaningful after invocation and usage reading are in place.

### 4. Agent catalog fourth
Discovery enrichment is important, but it is slightly less blocking than the missing telemetry and invocation paths.

### 5–7 follow naturally
Wrappers, classification, and skill packaging should be the stabilization layer.

---

## Phase 1 Definition Of Done

Phase 1 is complete when all the following are true:

- all required endpoints exist and return stable structured data
- all required wrapper scripts exist under `scripts/`
- wrappers use kernel endpoints only
- no direct DB-read script is required for the target workflow
- a supervising agent can perform the workflow without repo-layout discovery
- documentation identifies canonical vs diagnostic scripts
- a verification skill/runbook exists and references only canonical scripts/endpoints

---

## Phase 2 — Run The End-To-End Test Session

## Objective

After the gaps are filled, execute the budget-verification scenario using only the approved canonical surface.

## Preconditions

Before starting Phase 2, confirm:

- kernel is running and healthy
- all Phase 1 endpoints are live
- all Phase 1 scripts are available
- active agents are configured
- usage tracking is enabled
- budgeting engine is enabled and current
- the selected agents have access to their intended provider/key routes

---

## Canonical Workflow For The Test Session

## Step 1 — Discover Active Agents

### Goal
Obtain the official list of active agents and key metadata.

### Canonical endpoint/script
- endpoint: `GET /v1/agents` or equivalent canonical catalog path
- script: `scripts/runtime/list_agents.sh`

### Expected output
For each active agent:
- identity
- role/description
- manager relation
- provider/model summary
- budget mode
- current budget preview

### Why this step matters
It defines the target set for the test and ensures the caller is not relying on repo assumptions.

---

## Step 2 — Capture Baseline Budget Report

### Goal
Record the current budget state before any test calls.

### Canonical endpoint/script
- endpoint: `GET /v1/budgets/report`
- script: `scripts/budgets/get_budget_report.sh`

### Expected output
- company totals
- per-agent budget state
- current spend values
- remaining budget values
- allocation context

### Artifacts to retain
- machine-readable baseline report
- optional human-readable baseline summary

### Why this step matters
This is the reference point for later delta verification.

---

## Step 3 — Execute One Cheap Prompt Per Agent

### Goal
Cause a real, low-cost run for each target agent so usage and budget effects can be measured.

### Canonical endpoint/script
- endpoint: `POST /v1/agents/run`
- script: `scripts/runtime/run_agent_prompt.sh`

### Recommended prompt style
Use a cheap prompt, such as:
- “Write one short sentence about teamwork.”
- “Write a two-line poem about oranges.”
- “Return one short paragraph about planning.”

### Required practice
Use a unique `session_key` per run so later usage queries are deterministic.

### Expected output
For each run:
- success/failure status
- returned text
- session key
- run metadata

### Why this step matters
This is the real workload that should consume tokens/cost and change the budget state.

---

## Step 4 — Retrieve Session Usage Summaries

### Goal
Verify that each invocation produced measurable telemetry.

### Canonical endpoint/script
- endpoint: `GET /v1/usage/sessions/{session_key}/summary`
- script: `scripts/usage/get_session_usage.sh`

### Expected output
For each session:
- llm call count
- total tokens
- cost
- start/end timestamps
- session span
- model/provider information

### Why this step matters
This step proves that the system is capturing real spend and associating it correctly with the invoked sessions.

---

## Step 5 — Optional Node-Level Cross-Check

### Goal
Verify that session-level data also appears in node-level recent-session views.

### Canonical endpoint/script
- endpoint: `GET /v1/usage/nodes/{node_id}/recent-sessions`
- script: `scripts/usage/list_recent_sessions.sh`

### Expected output
The recent session list should include the sessions created in Step 3.

### Why this step matters
This helps validate both the session indexing path and the operator monitoring view.

---

## Step 6 — Capture Post-Run Budget Report

### Goal
Record the budget state after the test prompts have been executed.

### Canonical endpoint/script
- endpoint: `GET /v1/budgets/report`
- script: `scripts/budgets/get_budget_report.sh`

### Expected output
Compared with baseline:
- increased current spend for exercised nodes
- decreased remaining budget for exercised nodes
- updated roll-up totals as appropriate

### Why this step matters
This is the final verification that usage affects budget state.

---

## Step 7 — Compare Before/After Reports

### Goal
Produce a deterministic human-readable and machine-readable comparison.

### Canonical script
- `scripts/budgets/compare_budget_reports.py`

### Expected output
A comparison report that highlights:
- per-node spend deltas
- per-node remaining-budget deltas
- organization-level total deltas
- mismatches between usage telemetry and budget movement if any

### Why this step matters
It turns raw reports into a validation artifact suitable for operator review and later autonomous decision-making.

---

## Phase 2 Definition Of Done

The end-to-end test session passes when:

- all target agents are discovered through the canonical agent catalog path
- a baseline budget report is captured through the canonical budget path
- each target agent successfully completes a cheap prompt run through the canonical invocation path
- each run has a visible session usage summary through the canonical usage path
- the post-run budget report shows corresponding spend movement
- the comparison artifact shows expected deltas without unexplained gaps

---

## Failure Interpretation Guide

## Case 1 — Agent catalog call fails
### Likely cause
- missing endpoint implementation
- auth/routing issue
- runtime service exposure gap

### Interpretation
The system is not yet ready for autonomous discovery.

### Action
Fix the catalog surface before continuing.

---

## Case 2 — Budget report is unavailable or incomplete
### Likely cause
- report endpoint not implemented
- budget service response not shaped for reporting
- sync state not exposed

### Interpretation
The system may manage budgets internally, but it is not yet exposing them canonically.

### Action
Implement the budget report surface before claiming autonomous budget verification.

---

## Case 3 — Agent invocation fails but discovery and budget reporting work
### Likely cause
- missing invocation endpoint
- runtime integration gap
- provider/config issue per agent

### Interpretation
The system has inventory and budgets but still lacks an autonomous execution path.

### Action
Fix invocation contract and per-agent routing/configuration before continuing.

---

## Case 4 — Invocation succeeds but session usage summary is missing
### Likely cause
- usage read APIs missing
- usage persistence not wired correctly
- session key not recorded consistently

### Interpretation
Execution is happening, but telemetry is not accessible or not correctly indexed.

### Action
Fix usage-reading APIs and session correlation before continuing.

---

## Case 5 — Usage summary exists but budget report does not change
### Likely cause
- budget reconciliation gap
- waterfall engine not consuming usage state correctly
- report not reflecting updated budget state

### Interpretation
Telemetry and budgeting are not fully connected yet.

### Action
Investigate sync/reconciliation and report derivation before continuing.

---

## Case 6 — A developer-only script is still required to complete the workflow
### Likely cause
- missing canonical endpoint or wrapper
- incomplete productization of the workflow

### Interpretation
The workflow is not yet agent-operable, even if humans can finish it.

### Action
Record the missing canonical interface as a product gap and close it before claiming completion.

---

## Recommended Delegation Structure

This work can be delegated in modular slices.

## Agent A — Discovery Surface
Owns:
- agent catalog endpoint/schema
- `scripts/runtime/list_agents.sh`
- tests for agent discovery completeness

## Agent B — Budget Report Surface
Owns:
- budget report endpoint/schema
- `scripts/budgets/get_budget_report.sh`
- tests for before/after budget summaries

## Agent C — Invocation Surface
Owns:
- invoke-agent endpoint/schema
- `scripts/runtime/run_agent_prompt.sh`
- tests for single-agent execution and error handling

## Agent D — Usage Reporting Surface
Owns:
- usage read endpoints/schemas
- `scripts/usage/get_session_usage.sh`
- `scripts/usage/list_recent_sessions.sh`
- tests for session and node-level usage summaries

## Agent E — Packaging And Governance
Owns:
- script classification pass
- canonical vs diagnostic documentation
- verification skill/runbook packaging
- comparison helper script

This decomposition follows the project’s skill-first and modular development guidance.

---

## Documentation And Skill Follow-Up

When the implementation work is complete, update at least:

- `docs/documentation.md`
- `docs/current-task.md`
- `docs/plan.md`
- `.codex/skills/verify-budget-consumption-flow/SKILL.md`
- mirrored `skills/verify-budget-consumption-flow/SKILL.md` if skill mirroring remains required

Also document:

- which scripts are canonical wrappers
- which scripts are diagnostics only
- sample command sequences for operators and agents
- expected JSON output shapes where appropriate

---

## Final Recommended Sequence For The Team

### First
Implement the missing canonical surfaces in this order:
1. usage/session read APIs
2. agent invocation API
3. budget report API
4. enriched agent catalog
5. endpoint-only wrapper scripts
6. script classification and documentation
7. verification skill/runbook

### Then
Run the end-to-end workflow using only:
- canonical endpoints
- canonical wrapper scripts
- machine-readable artifacts for comparison

### Do not do this as proof of completion
- direct DB queries
- repo directory scans
- local runtime bootstrapping as the canonical path
- manual permission workarounds on behalf of the agents

Those may still be used for developer diagnosis, but they do not count as proof that the agentic workflow is complete.

---

## Conclusion

This plan intentionally puts implementation before demonstration.

That is the correct order because the desired demonstration is not simply “can a developer manually make this work?” but rather:

> can the OmniClaw control plane expose enough stable functionality that another Nanobot agent can discover, invoke, observe, and verify budget consumption without hidden human help?

Once the recommended endpoints and scripts are added, the final test session becomes meaningful as a true autonomous-system validation rather than a developer-assisted smoke test.
