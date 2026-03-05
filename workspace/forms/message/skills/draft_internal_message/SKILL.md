---
name: draft_internal_message
description: Create a `message` form draft and send it through the graph workflow.
---

## Inputs
- Receiver node name or node id (`target` frontmatter field)
- Short subject
- Message body

## Steps
1. Copy template `templates/message_draft.md` into `<workspace>/outbox/pending/<file>.md`.
2. Fill frontmatter:
   - `form_type: message`
   - `stage: DRAFT`
   - `decision: send`
   - `target: <receiver node name or id>`
3. Add subject/body content.
4. Leave the file in `outbox/pending/` for kernel scan.

## Validation
- Frontmatter contains non-empty `form_type`, `stage`, `decision`, `target`.
- `decision` is `send`.

## Fallback
- If IPC reports `undelivered`, fix frontmatter error and keep file in `outbox/pending/`.
