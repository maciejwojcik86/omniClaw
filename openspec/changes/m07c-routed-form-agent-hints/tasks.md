## 1. Router contract

- [x] 1.1 Add kernel-managed routed frontmatter field `agent`.
- [x] 1.2 Add kernel-managed routed frontmatter field `target_agent`.
- [x] 1.3 Clear routed `target` and reserve it for queue-time dynamic target input.

## 2. Frontmatter handling

- [x] 2.1 Add multiline block frontmatter parsing support in IPC router.
- [x] 2.2 Add multiline block frontmatter rendering support in IPC router.
- [x] 2.3 Mirror the same parsing/rendering behavior in IPC test helpers.

## 3. Guidance and documentation

- [x] 3.1 Update canonical heartbeat guidance to explain `agent`, `target_agent`, and `target`.
- [x] 3.2 Update affected deploy workflow skill guidance to stop treating `target` as the current holder.
- [x] 3.3 Update operator/developer docs and IPC skill documentation.

## 4. Verification

- [x] 4.1 Add or update IPC tests for `agent` / `target_agent`.
- [x] 4.2 Run `uv run pytest -q`.
- [x] 4.3 Run `openspec validate --type change m07c-routed-form-agent-hints --strict`.
