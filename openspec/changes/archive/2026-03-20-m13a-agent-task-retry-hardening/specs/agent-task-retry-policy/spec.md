## ADDED Requirements

### Requirement: Kernel SHALL Persist Retryable Agent Task Failures
The system SHALL persist canonical retry records for agent task executions that fail with retryable LLM/API conditions so deferred work survives process restarts and can be inspected later.

#### Scenario: Retryable failure is recorded
- **WHEN** an agent task execution fails with a retryable transient or budget-recoverable LLM/API condition
- **THEN** the system stores a retry record with task identity, failure classification, attempt count, next-attempt timestamp, and latest error summary

#### Scenario: Terminal failure is not queued
- **WHEN** an agent task execution fails with a terminal non-retryable condition
- **THEN** the system marks the execution as terminally failed without creating a pending retry schedule

### Requirement: Retry Scheduling SHALL Use Progressive Backoff
The system SHALL compute retry timing from a deterministic progressive backoff policy that increases wait time across repeated failures and supports long-horizon deferral for budget-recoverable conditions.

#### Scenario: Transient overload escalates gradually
- **WHEN** repeated attempts fail due to transient rate-limit or overload conditions
- **THEN** each subsequent retry is scheduled later than the previous retry until the policy cap is reached

#### Scenario: Budget-recoverable failure defers to long window
- **WHEN** an execution fails because credits, quota, or budget are temporarily exhausted and the condition is classified as recoverable later
- **THEN** the system schedules a long-delay retry window instead of looping through rapid short retries

### Requirement: Due Retries SHALL Resume Through Canonical Runtime Scheduling
The system SHALL resume due retries through a kernel-managed scheduler path rather than by keeping one runtime process sleeping until the retry window expires.

#### Scenario: Due retry becomes runnable after restart
- **WHEN** the kernel restarts while retry records remain pending
- **THEN** the scheduler reloads due retry records from canonical storage and resumes execution when their scheduled time arrives

#### Scenario: Retry is claimed once
- **WHEN** multiple scheduler passes encounter the same due retry record
- **THEN** the system allows only one retry execution claim for that scheduled attempt lineage

### Requirement: Retry Lifecycle SHALL Be Operator Visible And Controllable
The system SHALL expose canonical operator visibility and control over pending and exhausted retry records.

#### Scenario: Operator inspects pending retries
- **WHEN** an operator requests retry state for an agent or task
- **THEN** the system returns pending status, failure classification, attempt count, last error summary, and next-attempt timestamp

#### Scenario: Operator cancels or expedites a retry
- **WHEN** an operator issues a supported cancel or retry-now action for a pending retry
- **THEN** the system updates the retry record deterministically and reports the resulting state

### Requirement: Failure Telemetry SHALL Preserve Provider And Model Dimensions
The system SHALL record normalized failure telemetry for retryable and terminal LLM/API failures with provider and model dimensions in addition to agent and task context.

#### Scenario: Failure event captures shared upstream dimensions
- **WHEN** an LLM/API call fails during agent task execution
- **THEN** the system records the provider identifier, model identifier, normalized failure class, timestamp, and related agent/task context needed for grouped reporting

#### Scenario: Different agents share one provider incident trail
- **WHEN** multiple agents fail against the same provider or model during the same incident window
- **THEN** the telemetry can be queried or grouped by provider and model without requiring raw log inspection
