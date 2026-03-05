## ADDED Requirements

### Requirement: Form Type Keys SHALL Use Snake Case
Form type registry keys SHALL use snake_case naming.

#### Scenario: Snake case key is accepted
- **WHEN** an operator registers `feature_pipeline_form`
- **THEN** kernel accepts the key as valid registry input

#### Scenario: Non-snake-case key is rejected
- **WHEN** an operator submits uppercase/invalid symbols
- **THEN** kernel rejects mutation with key validation errors

### Requirement: Kernel SHALL Persist Versioned Form Type Definitions
The kernel SHALL persist form definitions with lifecycle states (`DRAFT`, `VALIDATED`, `ACTIVE`, `DEPRECATED`).

#### Scenario: Draft definition is created
- **WHEN** operator creates or updates a form definition
- **THEN** kernel stores requested version in canonical `form_types`

#### Scenario: Active version is unique per form type
- **WHEN** operator activates one version of a form type
- **THEN** kernel deactivates other active versions for that `type_key`

### Requirement: Preferred Workflow Schema SHALL Be Stage-Graph JSON
Each form definition SHALL support a stage-centric graph (`start_stage`, `end_stage`, `stages`) where each stage declares `target`, `required_skill`, and decision map.

#### Scenario: Stage defines required execution skill
- **WHEN** a stage is declared in workflow graph
- **THEN** `required_skill` points to master skill folder under `workspace/forms/<form_type>/`

#### Scenario: Stage graph requires end stage
- **WHEN** workflow is submitted without reachable `end_stage`
- **THEN** activation is rejected with validation errors

#### Scenario: Terminal stage can resolve no holder
- **WHEN** terminal stage uses `target: null` (or equivalent none marker)
- **THEN** decision resolves holder to `null`

#### Scenario: Legacy node-graph remains compatible
- **WHEN** existing node-centric workflows are loaded
- **THEN** decision engine can project them for compatibility, but stage-graph format remains preferred

### Requirement: Form Instances SHALL Bind Active Definition Version
A form instance SHALL record form type/version at creation, and decisions SHALL validate against that pinned version.

#### Scenario: Existing instance remains pinned after newer activation
- **WHEN** a newer definition version is activated
- **THEN** existing instances continue validating against originally bound version
