## ADDED Requirements

### Requirement: Report Retry State Canonically
The system SHALL provide a canonical report surface for retry state associated with agent task executions.

#### Scenario: Caller retrieves pending retry summary
- **WHEN** a caller requests retry state for a node, task, or recent execution window
- **THEN** the system returns retry status, failure classification, attempt count, next-attempt timestamp, and latest terminal or pending outcome metadata

#### Scenario: Caller distinguishes pending and exhausted retries
- **WHEN** a caller inspects retry reporting after repeated failures
- **THEN** the system distinguishes pending deferred retries from permanently exhausted or terminally failed executions

### Requirement: Report Provider And Model Failure Trends Canonically
The system SHALL provide a canonical report surface for grouped LLM/API failure trends by provider and model so shared upstream issues can be detected across agents.

#### Scenario: Caller spots degraded model across many agents
- **WHEN** a caller requests failure trend reporting for a recent time window
- **THEN** the system returns grouped counts and recent examples by provider, model, and normalized failure class

#### Scenario: Caller distinguishes upstream incident from one-agent issue
- **WHEN** failures are concentrated on one provider/model but span multiple agents
- **THEN** the reporting surface makes that shared upstream pattern visible without requiring per-agent log review
