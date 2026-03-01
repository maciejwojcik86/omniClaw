## Context

The codebase is currently at bootstrap stage with foundational vision docs and an empty OpenSpec spec tree. To execute a long milestone program safely, the project needs a strict delivery protocol that is human-readable and machine-actionable.

## Goals / Non-Goals

**Goals:**
- Encode governance rules in `AGENTS.md` so they persist across all sessions.
- Establish dedicated tracking docs for active work and backlog progression.
- Ensure OpenSpec artifacts are produced consistently for each milestone.
- Define update cadence for repository mapping and quality gates.

**Non-Goals:**
- Implement milestone M01+ runtime features.
- Introduce production APIs, daemons, or schema migrations in this change.
- Archive M00 in this same change.

## Decisions

- Store global governance in `AGENTS.md` to provide a single persistent execution contract.
- Use `docs/master-task-list.md` as the backlog ledger and `docs/current-task.md` as single active work card.
- Keep one active change at a time while tracking future milestones as planned rows in the master task list.
- Enrich `openspec/config.yaml` with project context/rules so artifact authoring is aligned with OmniClaw constraints.

## Risks / Trade-offs

- [Risk] Governance docs drift from actual repo state. -> Mitigation: mandatory repository-map updates after each completed change.
- [Risk] Overly rigid process slows early prototyping. -> Mitigation: keep milestone scopes small and one-change-at-a-time.
- [Risk] Tracker docs become stale. -> Mitigation: definition-of-done requires updating both tracker docs.
