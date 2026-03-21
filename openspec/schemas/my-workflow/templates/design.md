## Context

<!-- Background and current state -->

## Goals / Non-Goals

**Goals:**
<!-- What this design aims to achieve -->

**Non-Goals:**
<!-- What is explicitly out of scope -->

## Decisions

<!-- Key design decisions and rationale -->

## Risks / Trade-offs

<!-- Known risks and trade-offs -->

## Git Hygiene And Reviewability

### Working Tree Expectations
- Confirm whether implementation should proceed on a clean or mixed worktree.
- If mixed, describe how current-change files will be distinguished from unrelated local modifications.

### Failure Reporting Contract
- If a canonical command, migration, validation, or test fails:
  - record the exact command
  - record the exact file/path/config involved
  - explain expected vs actual behavior
  - state whether any workaround is temporary or the real fix
- Do not treat a workaround as closure until the canonical path is investigated.

### Commit / Push Review Plan
- Planned commit boundary for this change:
- Planned verification before commit:
- Planned push/reporting behavior at closure:
