## ADDED Requirements

### Requirement: Kernel SHALL Provide Form Type Administration Actions
Kernel SHALL expose deterministic actions for form lifecycle administration.

#### Scenario: Operator upserts and validates a form type
- **WHEN** operator submits `upsert_form_type` then `validate_form_type`
- **THEN** kernel stores definition and returns explicit validation results

#### Scenario: Operator activates a validated version
- **WHEN** operator submits `activate_form_type`
- **THEN** selected version becomes active for new form instances

#### Scenario: Operator deprecates or deletes a version
- **WHEN** operator submits `deprecate_form_type` or `delete_form_type`
- **THEN** kernel updates/removes requested version deterministically

### Requirement: Activation SHALL Validate Workspace Skill Master Copies
Activation SHALL fail when any stage `required_skill` is missing from workspace form package.

#### Scenario: Missing required skill blocks activation
- **WHEN** stage skill folder is absent at `workspace/forms/<form_type>/skills/<required_skill>/SKILL.md`
- **THEN** activation is rejected with missing-skill errors

### Requirement: Workflow JSON SHALL Be Persisted To Workspace Package
On successful upsert/activate, kernel SHALL persist canonical workflow copy to workspace package path.

#### Scenario: Workflow copy is written
- **WHEN** a form type is upserted or activated
- **THEN** kernel writes `workspace/forms/<form_type>/workflow.json`

### Requirement: Tooling SHALL Support Repeatable Workspace-Driven Publish Flow
Project SHALL include scriptable workflow publication from workspace JSON definition.

#### Scenario: Publish helper submits workspace workflow
- **WHEN** operator runs workflow publish helper
- **THEN** helper submits `upsert_form_type` payload derived from `workspace/forms/<form_type>/workflow.json`
