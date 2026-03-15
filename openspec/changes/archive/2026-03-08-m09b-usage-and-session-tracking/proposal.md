## Why

Currently, nanobots report limited usage statistics directly into their active sessions, and OmniClaw relies on external proxies like LiteLLM for overall budget enforcement. To achieve comprehensive observability, we need native tracking of tokens used, computed costs, and execution timings (request sent, generation start, generation finished) for each call by all agents, coupled with the ability to safely export and backup complete conversation sessions.

## What Changes

- Add native interception of LLM tracking data directly from provider responses (recording token usage, costs, and timing metrics) and persist this into an actionable database table or structured logs.
- Introduce session backup and export capabilities by pulling from Nanobot's native SessionManager JSONL files and persisting them into OmniClaw's canonical artifact storage or database.
- **BREAKING**: None expected.

## Capabilities

### New Capabilities
- `usage-logging`: Persistent tracking and real-time computation of tokens, estimated cost, and response times of every LLM call made by any active agent.
- `session-export`: A mechanism or endpoint allowing the kernel to capture, backup, and store complete conversation histories for auditing, context-seed reference, or compliance backups.

### Modified Capabilities
- `budget-management`: Expand budget tracking to natively encompass detailed per-call event ingestion in conjunction with LiteLLM proxy tracking or standalone provider stats.

## Impact

- **Database Schema**: Expected addition of new tables like `agent_llm_calls` for usage metrics and possibly `agent_session_backups` to track exported sessions.
- **Nanobot Integration**: Tighter coupling with Nanobot's `LLMResponse` and `SessionManager` within the core agent loop.
- **API Endpoints**: New `/v1/budgets/usage` and `/v1/sessions/export` routes.
