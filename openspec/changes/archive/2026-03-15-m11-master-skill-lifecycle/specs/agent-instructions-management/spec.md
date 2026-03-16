## MODIFIED Requirements

### Requirement: Instructions Access SHALL Follow Company-Configured Hierarchy Rules
The kernel SHALL continue to authorize instruction-management actions using the management hierarchy, and any manager-facing skill-management actions that specify an actor node SHALL use the same hierarchy scope policy.

#### Scenario: Manager skill actions follow the same scope rules
- **WHEN** a manager invokes skill assignment or removal actions with an actor node
- **THEN** the kernel authorizes the target agent using the same direct-children or descendant policy used for instruction management

#### Scenario: Manager-facing skills arrive through assignment-based reconciliation
- **WHEN** the kernel reconciles approved skills for a node with subordinates
- **THEN** manager-facing loose master skills assigned by policy or operator action are delivered through the shared assignment-based skill reconciliation path
- **AND** the kernel no longer depends on a hardcoded manager-skill copy loop
