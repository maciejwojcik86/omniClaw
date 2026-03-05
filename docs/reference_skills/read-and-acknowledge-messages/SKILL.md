---
name: read-and-acknowledge-messages
description: Agent/operator SOP for processing inbox unread messages, moving them to inbox read, and acknowledging read status in OmniClaw forms ledger.
license: MIT
compatibility: OmniClaw M06 forms actions + IPC scripts
metadata:
  author: omniclaw
  version: "0.1"
---

Use this skill when an incoming `message` form has status `WAITING_TO_BE_READ` (legacy `SENT` also supported) and the holder has read/processed it.

## Scope

This skill covers:
- locating unread files in `inbox/unread`
- moving handled files to `inbox/read`
- calling forms action `acknowledge_message_read` to decision `WAITING_TO_BE_READ -> ARCHIVED`
- ensuring holder-specific acknowledgement
- stage template reference:
  - `.codex/skills/read-and-acknowledge-messages/templates/message/waiting_to_be_read.md`

## Required Inputs

- Workspace root path
- `message-file` name currently in `inbox/unread`
- `form_id` from ledger/scan output
- `actor_node_id` of current holder node

## Execution Steps

1. Read and process message in `inbox/unread/<message-file>`.
2. Acknowledge with helper script:
   - `./scripts/ipc/acknowledge_message_read.sh --apply --workspace-root <workspace> --message-file <file> --form-id <form_id> --actor-node-id <holder_node_id>`
3. Script moves file to `inbox/read` and posts `/v1/forms/actions` acknowledge action.
4. Confirm form status is now `ARCHIVED`.

## Verification Commands

- Dry-run:
  - `./scripts/ipc/acknowledge_message_read.sh --workspace-root <workspace> --message-file <file> --form-id <form_id> --actor-node-id <holder_node_id>`
- Check mailbox state:
  - `find <workspace>/inbox -maxdepth 2 -type f | sort`
- Optional check via API:
  - `./scripts/forms/trigger_forms_action.sh --apply --action transition_form --form-id <form_id>`

## Fallback Path

If acknowledgement fails:
1. Verify actor node id matches `current_holder_node` in DB.
2. Confirm form currently has status `WAITING_TO_BE_READ` (or legacy `SENT`).
3. If file move already happened but API failed, re-run only the forms action with `acknowledge_message_read` payload.
