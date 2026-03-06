---
name: draft-internal-message
description: Create a `message` form draft and send it through the graph workflow.
---

## Inputs
- Exact receiver agent name (`target` frontmatter field in YAML)
- Short subject
- Message body

## Steps
1. Copy template `templates/message_draft.md` into `<workspace>/outbox/pending/<file>.md`.
2. Fill frontmatter:
   - `form_type: message`
   - `stage: DRAFT`
   - `decision: send`
   - `target: <exact receiver agent name>` (must match the real agent name exactly)
3. Add subject/body content.
4. Leave the file in `outbox/pending/` for kernel scan.

## Validation
- Frontmatter contains non-empty `form_type`, `stage`, `decision`, `target`.
- `decision` is `send`.
- `target` is the correct intended receiver agent name, written exactly in YAML frontmatter (no alias, typo, or wrong id).

## Fallback
- If IPC reports `undelivered`, fix frontmatter error and keep file in `outbox/pending/`.
