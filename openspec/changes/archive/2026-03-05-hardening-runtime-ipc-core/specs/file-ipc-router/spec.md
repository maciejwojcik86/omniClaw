## ADDED Requirements

### Requirement: IPC Scan SHALL Stop Processing After Requested Limit
The IPC router MUST stop queue traversal once the requested scan limit is reached.

#### Scenario: Limit reached in large queue
- **WHEN** scan is invoked with limit `N` and queue contains more than `N` files
- **THEN** no more than `N` eligible files are processed in that scan cycle

### Requirement: IPC Auto-Scan SHALL Run via Non-Blocking Execution Path
Kernel auto-scan loop MUST run filesystem scan work outside the asyncio event loop thread.

#### Scenario: Auto-scan enabled with high queue depth
- **WHEN** background scan executes repeatedly
- **THEN** health and control endpoints remain responsive while scan work runs
