## ADDED Requirements

### Requirement: Record LLM Token Usage
The system SHALL intercept and persist detailed usage metrics natively from LLM provider responses (input tokens, output tokens, reasoning tokens).

#### Scenario: Successful response parsing
- **WHEN** an agent completes a chat call via the `LLMProvider`
- **THEN** the token usage and cost is persisted to an `agent_llm_calls` log associated with the agent's ID

### Requirement: Record Request Timing
The system SHALL capture timing metadata for each LLM provider call, including request start time and response end time.

#### Scenario: Timing completion
- **WHEN** an agent issues a chat query
- **THEN** both the `start_time` and `end_time` are accurately recorded and saved to the usage log
