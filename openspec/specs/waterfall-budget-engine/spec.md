# waterfall-budget-engine Specification

## Purpose
TBD - created by archiving change m10-waterfall-budget-engine. Update Purpose after archive.
## Requirements
### Requirement: Company Budget SHALL Cascade Through Direct-Report Allocations
The system SHALL maintain a company-level daily budget pool and distribute it through the management hierarchy using each manager's saved direct-report percentage allocations. Any budget not assigned to direct reports SHALL remain as the manager's retained department reserve.

#### Scenario: Root pool allocation computes first team layer
- **WHEN** the daily budget cycle runs with a configured company budget and saved allocations for the root allocator node
- **THEN** the system computes fresh daily inflow for the root allocator's direct reports according to their saved percentages and retains the unallocated remainder for the allocator

#### Scenario: Downstream team uses saved shares after upstream change
- **WHEN** an upstream manager's incoming pool changes
- **THEN** the system recomputes every affected subtree immediately using the most recently saved direct-report allocations for each downstream manager

### Requirement: Daily Budget Cycle SHALL Reset Spend And Carry Forward Reserve
The system SHALL run a daily budget cycle that resets node spend, carries unused allowance into reserve, records an auditable cycle entry, and recalculates fresh inflow for the new day.

#### Scenario: Daily cycle resets and rolls reserve
- **WHEN** the scheduled daily budget cycle executes
- **THEN** each node's current spend resets to zero, unused prior allowance is added to reserve, and the new day's inflow is recalculated from the hierarchy

#### Scenario: Missed cycle catches up safely
- **WHEN** the kernel restarts after the configured cycle time has passed without a completed cycle for the current UTC date
- **THEN** the system executes the cycle once for the missing date and does not duplicate it on the same day

### Requirement: Budget Modes SHALL Control Enforcement Behavior
The system SHALL support `metered` and `free` budget modes. Metered nodes SHALL receive enforced effective caps. Free nodes SHALL be visible in waterfall reporting but SHALL not receive enforced runtime caps or over-budget warnings.

#### Scenario: Metered node receives enforced cap
- **WHEN** a metered node's effective allowance changes
- **THEN** the system recalculates its remaining budget and syncs the resulting cap to the provider integration

#### Scenario: Free node remains visible without enforced cap
- **WHEN** a free node appears in a team budget view or waterfall recalculation
- **THEN** the system includes its reserve and inflow values in reporting without applying a provider cap update

### Requirement: Budget Change Propagation SHALL Require Manager Follow-Up
The system SHALL notify direct reports whenever their effective budget changes. Direct reports who also manage others SHALL be marked for review and instructed to reapply their own team split and communicate further changes downward.

#### Scenario: Worker receives budget change message
- **WHEN** a manager updates direct-report allocations
- **THEN** each affected direct report receives a kernel-authored budget change message describing the reason, impact, and updated numbers

#### Scenario: Downstream manager is marked for review
- **WHEN** an affected direct report has subordinates of its own
- **THEN** the system marks that node as requiring budget review and includes reallocation instructions in the change message

