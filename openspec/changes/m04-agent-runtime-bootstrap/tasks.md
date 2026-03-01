## 1. Runtime Bootstrap Foundations

- [ ] 1.1 Add runtime configuration fields for command template, timeout, and output boundaries.
- [ ] 1.2 Create runtime bootstrap service contract and command builder with user-context execution support.

## 2. Runtime Bootstrap Implementation

- [ ] 2.1 Implement seed-file initialization for `~/.nullclaw/workspace/notes/TODO.md` and `~/.nullclaw/workspace/persona_template.md`.
- [ ] 2.2 Implement runtime launch execution with metadata capture (timestamps, command, exit status, artifact paths).
- [ ] 2.3 Expose kernel runtime bootstrap endpoint and response schema.

## 3. Verification and Documentation

- [ ] 3.1 Add unit tests for command building, seed logic, and metadata capture.
- [ ] 3.2 Add system smoke script and usage notes for restricted runtime execution.
- [ ] 3.3 Run `uv run pytest -q` and `openspec validate --type change m04-agent-runtime-bootstrap --strict`.
