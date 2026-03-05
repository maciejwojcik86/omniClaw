## MODIFIED Requirements

### Requirement: IPC Router SHALL Process Generic Forms Through Canonical State Machine
The kernel SHALL route queued markdown forms (not message-only payloads) through active form-type graph definitions stored in `form_types`.

#### Scenario: Form routed successfully
- **WHEN** a queued form includes valid frontmatter (`form_type`, `stage`, `decision`) and decision edge exists
- **THEN** the kernel routes the file to the next holder workspace (when holder exists), updates canonical status/holder via decision engine, and appends a decision event

#### Scenario: Dynamic target resolution is supported
- **WHEN** a stage target uses `{{initiator}}`, `{{any}}`, or `{{var}}`
- **THEN** IPC resolves target node deterministically from frontmatter/context and routes to exactly one holder (or no holder for terminal stages)

#### Scenario: Routed-form backup is retained
- **WHEN** IPC routes a form decision
- **THEN** a backup copy is written under `workspace/form_archive/<form_type>/<form_id>/...`

#### Scenario: Required stage skill is distributed
- **WHEN** IPC routes a form to a stage with `required_skill`
- **THEN** kernel validates master skill exists in `workspace/forms/<form_type>/skills/<required_skill>/SKILL.md` and copies skill package to participant workspaces

#### Scenario: Undelivered form remains queued
- **WHEN** a queued form fails validation, target resolution, or workflow checks
- **THEN** no decision is committed and the source file remains in sender queue with failure reason in IPC response

#### Scenario: MESSAGE compatibility alias remains available
- **WHEN** operator triggers IPC action `scan_messages` or submits legacy `type: MESSAGE`
- **THEN** kernel maps behavior to generic form routing with `form_type: message`
