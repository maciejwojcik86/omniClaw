## MODIFIED Requirements

### Requirement: Router Filesystem Lifecycle SHALL Be Deterministic
The router SHALL apply deterministic file transitions for routed and undelivered outcomes.

#### Scenario: Successful delivery transitions to archive
- **WHEN** form routing succeeds
- **THEN** sender-side queued file transitions from pending queue to archive path while a delivered copy exists in destination inbox when next holder exists

## ADDED Requirements

### Requirement: Routed Forms SHALL Include Kernel-Managed Stage Skill Guidance
The IPC router MUST write `stage_skill` into routed frontmatter as kernel-managed metadata for the next stage holder.

#### Scenario: Non-terminal next stage with required skill
- **WHEN** queued form transitions to next stage that declares `required_skill`
- **THEN** routed frontmatter includes `stage_skill` set to that next-stage required skill name

#### Scenario: Existing stage_skill in source frontmatter
- **WHEN** queued source file contains `stage_skill` value
- **THEN** kernel overwrites it with the resolved next-stage value before delivery/archive

#### Scenario: Terminal no-holder next stage
- **WHEN** queued form transitions to terminal stage with no holder target (`null`/`none`)
- **THEN** routed frontmatter includes `stage_skill` with empty string value
