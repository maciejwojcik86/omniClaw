## ADDED Requirements

### Requirement: Canonical Node Metadata SHALL Track Instruction Template Inputs
The canonical node model SHALL persist the role label and external instruction template root needed to render managed AGENT instructions.

#### Scenario: Node metadata migration completes
- **WHEN** the database is migrated for the context injector change
- **THEN** canonical node records include `role_name` and `instruction_template_root` columns without losing existing node data

#### Scenario: Repository persists instruction metadata
- **WHEN** higher-level services create or update a node with instruction metadata
- **THEN** repository operations persist and return the node role label and template-root path alongside existing runtime metadata
