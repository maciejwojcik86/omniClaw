## ADDED Requirements

### Requirement: Master Skill Catalog SHALL Resolve Active Company Skill Roots From The Selected Company Workspace
The kernel SHALL scan loose company skills from the selected company workspace `master_skills/` root and SHALL resolve form-linked skill packages from the selected company workspace `forms/` root.

#### Scenario: Loose company skill is discovered under selected workspace
- **WHEN** the skills service syncs the company master-skill catalog
- **THEN** it scans `<company-workspace-root>/master_skills/`
- **AND** catalogs only the loose skill packages found under that selected company workspace root

#### Scenario: Form-linked skill is resolved from selected workspace
- **WHEN** a workflow package is activated or synced
- **THEN** the kernel resolves stage skill sources from `<company-workspace-root>/forms/<form_type>/skills/`
- **AND** stores those selected-workspace source paths in the master-skill catalog

### Requirement: Retired Company Skill Roots SHALL Remain Outside Active Skill Distribution
The selected company workspace SHALL provide retired/discontinued skill roots, and the kernel SHALL exclude those roots from active master-skill discovery and agent skill reconciliation.

#### Scenario: Retired loose skill package exists
- **WHEN** a loose skill package is stored under the selected company workspace retired skill root
- **THEN** it is not returned by active loose-skill list actions
- **AND** it is not copied into agent workspaces during approved skill reconciliation
