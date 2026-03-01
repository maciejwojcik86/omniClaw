## Why

OmniClaw currently has vision documents but lacks an enforceable delivery contract for day-to-day engineering work. We need a concrete governance baseline so every future milestone is executed consistently via OpenSpec with auditable tracking.

## What Changes

- Define project-level governance requirements for mission, scope boundaries, and execution order.
- Establish canonical task tracking artifacts (`docs/current-task.md`, `docs/master-task-list.md`).
- Formalize OpenSpec workflow rules and definition-of-done gates in `AGENTS.md`.
- Enrich `openspec/config.yaml` with project context and artifact rules tailored to OmniClaw.

## Capabilities

### New Capabilities
- `governance-bootstrap`: Establishes mandatory governance documents, tracking contracts, and OpenSpec operating rules.

### Modified Capabilities
- None.

## Impact

- Affected docs: `AGENTS.md`, `docs/master-task-list.md`, `docs/current-task.md`.
- Affected OpenSpec config: `openspec/config.yaml`.
- Affected process: all future `openspec/changes/*` authoring and implementation flow.
