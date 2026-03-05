## ADDED Requirements

### Requirement: Gateway Control SHALL Validate Host and Use Safe Command Invocation
Gateway start actions MUST validate host input and execute launch commands without shell-injection exposure.

#### Scenario: Valid host starts gateway
- **WHEN** a gateway start request uses a valid host value
- **THEN** runtime command execution proceeds and gateway state is updated

#### Scenario: Invalid host is rejected
- **WHEN** a gateway start request uses an invalid or unsafe host value
- **THEN** the request fails with HTTP 422 and no gateway process is started
