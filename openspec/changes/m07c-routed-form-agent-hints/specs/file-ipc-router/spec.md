## MODIFIED Requirements

### Requirement: Routed Forms SHALL Include Kernel-Managed Stage Skill Guidance
The IPC router MUST write kernel-managed routed metadata for the current delivered stage.

#### Scenario: Routed form includes current holder metadata
- **WHEN** a queued form is delivered to the next stage holder
- **THEN** routed frontmatter includes `agent` set to the current routed stage holder name

#### Scenario: Routed form includes next-hop decision hints
- **WHEN** a queued form is delivered to a stage that has outgoing workflow decisions
- **THEN** routed frontmatter includes `target_agent` showing the next holder options for each allowed decision of the current routed stage

#### Scenario: Initiator target is resolved in decision hints
- **WHEN** an outgoing decision leads to a stage targeted at `{{initiator}}`
- **THEN** routed `target_agent` shows the resolved initiator node name instead of the raw token

#### Scenario: Delivered routed form clears target input
- **WHEN** a form is delivered to `inbox/new`
- **THEN** routed frontmatter clears `target` so it is available only for later queue-time dynamic target input

#### Scenario: Terminal no-holder stage clears routed agent hints
- **WHEN** queued form transitions to terminal stage with no holder target (`null`/`none`)
- **THEN** routed frontmatter includes `agent: ""` and `target_agent: ""`
