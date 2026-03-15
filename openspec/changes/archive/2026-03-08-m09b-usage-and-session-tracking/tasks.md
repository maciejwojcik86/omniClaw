## 1. Database and Schematic Updates

- [x] 1.1 Create SQLAlchemy models for `AgentLLMCall` and `AgentSessionExport`.
- [x] 1.2 Generate and run Alembic migrations to apply these tables.

## 2. Token Usage Instrumentation

- [ ] 2.1 Update `nanobot.providers.base.LLMResponse` parsing or injection to ensure consistency of `usage` schema.
- [ ] 2.2 Modify `nanobot.agent.loop.AgentLoop._process_message` or `_run_agent_loop` to extract `LLMResponse` usage and insert into the database natively.
- [ ] 2.3 Record precise timing elements (request start, generation done) wrapping the `self.provider.chat()` invocation.

## 3. Session Export Module

- [ ] 3.1 Expose an internal service method `export_agent_session` mapping from `SessionManager`'s JSONL into the new table/canonical artifact storage.
- [ ] 3.2 Create the FastAPI route `POST /v1/sessions/export` accepting a node ID to trigger this payload.

## 4. Verification and Skill Capture

- [ ] 4.1 Write integration tests verifying database insertions from a mocked `LLMResponse`.
- [ ] 4.2 Execute a session export loop manually over an active test node.
- [ ] 4.3 Update `.codex/skills/manage-agent-budgets/SKILL.md` (or analogous observability skill) reflecting the new queries or CLI endpoints to retrieve tokens/sessions.
