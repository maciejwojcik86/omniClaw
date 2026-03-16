## ADDED Requirements

### Requirement: IPC Router SHALL Resolve Form Package And Archive Roots From The Selected Company Workspace
The IPC router SHALL load active workflow packages from the selected company workspace forms root and SHALL write archive copies to the selected company workspace archive root.

#### Scenario: Router loads active workflow package
- **WHEN** the router or forms service needs a workflow definition or stage skill package
- **THEN** it resolves those assets from `<company-workspace-root>/forms/`
- **AND** it does not depend on `<repo-root>/workspace/forms/`

#### Scenario: Router writes archive copy
- **WHEN** a routed form is archived successfully
- **THEN** the archive copy is written under the selected company workspace archive root
- **AND** the sender and holder workspace transitions still use canonical node workspace paths
