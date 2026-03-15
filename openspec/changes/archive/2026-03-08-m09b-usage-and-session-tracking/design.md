## Context

Currently, the OmniClaw framework delegates token usage and budgeting to LiteLLM's proxy tracking, but local environments without PostgreSQL can't natively ingest LiteLLM's proxy token DB. Additionally, Nanobot's provider `LLMResponse` natively sees token usage right after a successful `/v1/chat/completions` API call. Exporting JSONL sessions is also critical for operators to review historical transcripts across agents without sshing into the agents' workspaces directly.

## Goals / Non-Goals

**Goals:**
- Extract token usage natively from Nanobot's provider responses during the agent loop.
- Save these usage metrics securely into the OmniClaw database (`agent_llm_calls` table).
- Provide a kernel-level API endpoint to trigger or download complete session backups (`/v1/sessions/export`).

**Non-Goals:**
- Real-time token dashboard UI (we are just setting up the backend DB logging and API).
- Parsing unstructured text logs for costs; we strictly rely on the JSON `LLMResponse.usage` data.

## Decisions

**1. Intercepting Token Usage in the Agent Loop**
- *Rationale*: Nanobot's `AgentLoop._process_message` inherently calls `self.provider.chat()`, which returns an `LLMResponse` object populated with `usage` dict containing `prompt_tokens`, `completion_tokens`, and sometimes `thinking_tokens`.
- *Alternative Rejected*: Hooking directly into `SessionManager`'s I/O to read token logs would be brittle and tightly coupled to the message format rather than the provider contract.

**2. Storing Metrics in OmniClaw Database vs. Nanobot Workspace**
- *Rationale*: OmniClaw is the central orchestrator and budget enforcer. Pushing usage to OmniClaw's canonical SQLite/PostgreSQL `KernelRepository` allows cross-agent analytics and aggregated queries.
- *Alternative Rejected*: Storing metrics in a new JSON file inside the `nanobot/workspace/` limits cross-node querying capabilities.

## Risks / Trade-offs

- **[Risk] Syncing Asynchronous Calls** → *Mitigation*: The usage ingestion should immediately follow the `self.provider.chat()` execution and not block the critical path of the agent's LLM tools interaction indefinitely. Wait on insertion gracefully.
- **[Risk] Varying Provider Token Schemas** → *Mitigation*: Ensure the `usage` dict mapped on `LLMResponse` normalizes the keys (e.g., `prompt_tokens` vs `input_tokens`), safely falling back to 0 if keys are missing from older models.
