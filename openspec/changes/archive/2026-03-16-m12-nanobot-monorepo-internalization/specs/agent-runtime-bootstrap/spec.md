## ADDED Requirements

### Requirement: Runtime Bootstrap SHALL Use Installed Nanobot CLI With Explicit Integration Context
The kernel SHALL launch Nanobot runtime commands through the installed runtime binary and SHALL provide OmniClaw-managed integration context through explicit environment variables rather than through hardcoded external source paths.

#### Scenario: Kernel invokes runtime for prompt or gateway action
- **WHEN** the runtime service launches a Nanobot prompt or gateway command
- **THEN** it invokes the configured runtime binary command
- **AND** it provides explicit OmniClaw runtime integration environment values for database, node identity, and runtime output roots

### Requirement: Runtime Artifact Paths SHALL Expose Prompt Log Root
The runtime service SHALL expose the prompt-log artifact root alongside other runtime artifact paths for OmniClaw-managed Nanobot executions.

#### Scenario: Prompt invocation reports artifact paths
- **WHEN** the kernel returns runtime action metadata for an agent invocation
- **THEN** the artifact payload includes the runtime output root
- **AND** includes the prompt-log root under that runtime output boundary
