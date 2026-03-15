## Context

The IPC router already knows enough to determine both the current holder of a routed stage and the possible next holders for each allowed decision. That information is not surfaced cleanly in delivered form headers today, which makes agents guess from workflow JSON or from stale `target` values.

## Decisions

### 1. `agent` is kernel-managed current-holder metadata

- Router writes `agent` on every routed hop.
- Value is the routed stage holder name.
- Terminal/no-holder stages write `agent: ""`.

### 2. `target_agent` is kernel-managed next-hop guidance

- Router writes `target_agent` on every routed hop.
- Value is a readable decision map for the current routed stage, for example:

  ```yaml
  target_agent: |
    Leave one option that matches the chosen decision and delete the others:
    approve_to_director: Macos_Supervisor
    return_to_hr: HR_Head_01
  ```

- If all outgoing decisions lead to no-holder terminal stages, router writes `target_agent: ""`.

### 3. `target` remains a queue-time input only

- Delivered routed forms no longer use `target` to mean “current holder”.
- Delivered routed forms clear `target`.
- Agents only fill `target` before queueing when the chosen route requires a dynamic target (`{{any}}` / `{{var}}`).

### 4. Frontmatter parser supports multiline block values

- Router frontmatter parsing/rendering is extended to support `|` block scalars.
- This change is intentionally small-scope and does not attempt full YAML support.
- Test helpers mirror the same behavior so routed-form round-trips stay deterministic.

## Consequences

- Agents get explicit current-stage ownership without needing graph inference.
- Agents can see next-hop options without having to read workflow JSON.
- Existing workflows keep the same transition engine semantics; only routed header metadata changes.
