## Why

<!-- Explain the motivation for this change. What problem does this solve? Why now? -->

## What Changes

<!-- Describe what will change. Be specific about new capabilities, modifications, or removals. -->

## Capabilities

### New Capabilities
<!-- Capabilities being introduced. Replace <name> with kebab-case identifier (e.g., user-auth, data-export, api-rate-limiting). Each creates specs/<name>/spec.md -->
- `<name>`: <brief description of what this capability covers>

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing (not just implementation).
     Only list here if spec-level behavior changes. Each needs a delta spec file.
     Use existing spec names from openspec/specs/. Leave empty if no requirement changes. -->
- `<existing-name>`: <what requirement is changing>

## Git / Change Boundary Review

<!-- Mandatory before implementation starts and again before archive.
Record the real repo state instead of assuming a clean worktree. -->

### Starting Git State
- `git status --short` summary:
- Is the repo already dirty before this change? `yes/no`
- If yes, list unrelated or pre-existing modified areas:

### Intended Change Boundary
- Files/directories expected to change for this OpenSpec change:
- Files/directories explicitly out of scope:

### Commit / Push Expectation
- Expected commit strategy for this change:
- Should archive happen only after commit? `yes/no`
- Should push happen as part of closure? `yes/no`

## Impact

<!-- Affected code, APIs, dependencies, systems -->
