---
name: send_message
description: Agent SOP for drafting, reviewing, and submitting OmniClaw MESSAGE files from outbox drafts to pending queue.
license: MIT
compatibility: Nullclaw agent workspace with OmniClaw M05 file IPC router
metadata:
  author: omniclaw
  version: "0.1"
---

Use this skill when an agent needs to send a formal `MESSAGE` file to a HUMAN or AGENT node.

## Scope

This skill covers:
- Required MESSAGE frontmatter fields.
- Draft-review-submit workflow.
- Queue submission path scanned by kernel router.
- Troubleshooting when a message is undelivered.

## Required Inputs

- Sender node name (`sender`) exactly as registered in OmniClaw DB.
- Target node name (`target`) exactly as registered in OmniClaw DB.
- Message subject (`subject`).
- Message file name ending in `.md` (kernel derives `message_name` from source file path).

## MESSAGE Template

Primary template file:
- `.codex/skills/send_message/templates/message/draft.md`

Use this template and save it with a descriptive `.md` file name:

```markdown
---
type: MESSAGE
sender: <Sender_Node_Name>
target: <Target_Node_Name>
subject: <Short Subject>
---

# <Optional Heading>

<Main message content>

## Requested Action

- <clear request>

## Context

- <supporting detail>
```

## Execution Steps

1. Draft message in:
   - `<workspace>/outbox/drafts/<file-name>.md`
2. Review checklist:
   - `type` is exactly `MESSAGE`
   - `sender` is your exact node name
   - `target` is correct node name
   - `subject` is clear and short
   - body is complete and actionable
3. Submit by moving file to send queue:
   - move from `outbox/drafts/` to `outbox/pending/`
4. Wait for kernel router cycle.
5. Kernel will send a message and leave a copy depending on the outcome:
   - success: your file moved to `outbox/archive/`
   - undelivered: your file remains in `outbox/pending/` and scan response includes failure reason

## Verification Commands

- Check queue/archive paths:
  - `find outbox -maxdepth 2 -type f | sort`
- Optional operator-triggered scan:
  - `./scripts/ipc/trigger_ipc_action.sh --apply --action scan_messages`

## Fallback Path

If message stays undelivered in `outbox/pending`:
1. Review scan response `failure_reason` and fix frontmatter fields.
2. Confirm `target` node name is valid and target workspace exists.
3. Keep message in `outbox/pending/` for next routing cycle.
