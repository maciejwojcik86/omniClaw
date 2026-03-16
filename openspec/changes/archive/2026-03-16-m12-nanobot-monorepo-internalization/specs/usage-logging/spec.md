## ADDED Requirements

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
