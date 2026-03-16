# usage-logging Specification

## Purpose
TBD - created by archiving change m09b-usage-and-session-tracking. Update Purpose after archive.
## Requirements
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

### Requirement: OmniClaw-Managed Nanobot Calls SHALL Persist Usage Through Optional Runtime Integration
Nanobot SHALL load an optional runtime integration only when OmniClaw launches it with explicit integration context, and that hook SHALL persist provider-native usage data without relying on direct external-checkout imports.

#### Scenario: OmniClaw-managed runtime call completes
- **WHEN** an OmniClaw-managed Nanobot call finishes with native usage metadata
- **THEN** the optional runtime integration persists the usage record to canonical OmniClaw storage
- **AND** standalone Nanobot runs without that integration context remain runnable without OmniClaw

### Requirement: OmniClaw-Managed Nanobot Calls SHALL Write Final Prompt Payload Artifacts
OmniClaw-managed Nanobot provider calls SHALL persist the final provider request body that is about to be sent for inference under the runtime prompt-log artifact root.

#### Scenario: LiteLLM or Codex provider request is assembled
- **WHEN** the provider has finished assembling the outbound request body for an OmniClaw-managed call
- **THEN** the final request payload is written to a JSON artifact under the runtime `prompt_logs/` root
- **AND** auth headers, transport credentials, and API keys are excluded from that artifact
