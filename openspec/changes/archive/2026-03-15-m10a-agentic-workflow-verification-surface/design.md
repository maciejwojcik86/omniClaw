# Design

## Overview

This change productizes the verification path for the M10 budget system by completing the missing canonical control-plane surfaces required for autonomous testing. The design goal is not to invent new budgeting behavior, but to ensure the already implemented runtime, usage, and waterfall budget features can be discovered, exercised, and verified through stable interfaces available to Nanobot agents.

The design follows the evaluation and implementation guidance documented in:
- `docs/agentic-workflow-gap-analysis.md`
- `docs/agentic-workflow-implementation-and-test-plan.md`

## Goals

1. Provide one canonical discovery path for active agents.
2. Provide one canonical report path for current budget state.
3. Provide one canonical prompt-execution path for low-cost test calls.
4. Provide canonical usage/session summary reads for correlation and spend analysis.
5. Provide packaged helper scripts that wrap only supported endpoints/runtime contracts.
6. Make the final workflow repeatable by both operators and supervising agents.

## Non-Goals

- Replacing the underlying waterfall engine math introduced in M10.
- Introducing a separate orchestration subsystem for long-running workflow execution.
- Expanding the milestone into unrelated future capabilities.

## Architecture Changes

### 1. Agent catalog surface

Add a read-oriented agent catalog surface that returns active nodes with joined metadata from runtime, budget, and provider configuration state. This may be implemented either as:
- `GET /v1/agents`
- or as an enriched `list_agents` runtime action if the project prefers the existing action pattern

The response must be rich enough that callers do not need to inspect repo-local config files to understand what agents are available and what budget/runtime context they have.

### 2. Budget report surface

Add a canonical report response for organization/team budget state. The report should be stable enough to support machine comparison between a pre-run baseline and a post-run snapshot.

Preferred shape:
- `GET /v1/budgets/report`

Acceptable fallback:
- `POST /v1/budgets/actions` with a dedicated report action

This should be backed by the canonical budget tables and current waterfall engine state, not by local ad hoc report assembly.

### 3. Agent invocation surface

Add a kernel-mediated prompt execution operation for inexpensive verification runs. This should accept a target node plus a message and return structured execution metadata including the session key.

Preferred shape:
- `POST /v1/agents/run`

Acceptable fallback:
- runtime action `run_agent_prompt`

This creates a product-level invocation contract so supervisors do not need developer-style repo-local bootstrapping knowledge.

### 4. Usage/session summary surfaces

Add read APIs over the canonical usage persistence so callers can ask for:
- usage summary for a specific session key
- recent sessions for a node
- optional per-node summary rollups

These routes should return concise structured telemetry and must not require direct DB access by the caller.

### 5. Canonical wrapper scripts and classification

Every step in the final verification workflow should have a packaged script wrapper under `scripts/` where practical. Each script used in the final workflow must be endpoint-backed and clearly classified as canonical.

Diagnostic scripts that still use direct DB reads or repo-local inspection may remain for developer troubleshooting, but they must not be the official verification path.

## Data And Response Principles

### Stable machine-readable output

All new report/query surfaces should return predictable JSON structures suitable for automation and diffing.

### Explicit correlation keys

Prompt execution and usage reads must agree on `session_key` so the workflow can deterministically correlate runs with recorded cost and timing.

### Read/report versus mutation separation

Budget report and usage report surfaces should be read-optimized and not require callers to trigger unrelated mutations just to inspect state. If cost reconciliation is required before reporting, it should be explicit via either:
- a dedicated sync action followed by a report read, or
- a report option that clearly declares sync behavior

## Verification Flow

The final intended canonical workflow is:
1. list agents
2. capture baseline budget report
3. invoke one cheap prompt per target agent
4. fetch session usage summaries
5. capture post-run budget report
6. compare deltas

The change is only complete when this workflow can be run without:
- repo directory scanning
- direct SQLite reads
- manual developer runtime bootstrapping as the canonical path

## Testing Strategy

Add automated tests for:
- agent catalog response shape and metadata coverage
- budget report structure and expected values
- prompt invocation request/response and error cases
- usage summary and recent-session reporting
- final workflow composition using the canonical endpoints/scripts

Where shell wrappers are added, include smoke tests or script-level verification commands in documentation/skills.

## Documentation And Skills

Update:
- `docs/current-task.md`
- `docs/plan.md`
- `docs/documentation.md`
- `docs/implement.md`

Add or update skills so the new workflow is preserved as reusable SOP knowledge, including the final verification runbook for budget consumption flow.
