---
name: read_and_acknowledge_internal_message
description: Acknowledge and archive unread `message` forms with one tool call.
---
Inspect `inbox/unread/` for unread message forms.

For each unread message form:
   - Read and understand the message.
   - If a response is needed, draft a reply message using following `draft_internal_message` skill.

   - Acknowledge/archive the received message by running exactly:
     - `python3 skills/read_and_acknowledge_internal_message/scripts/acknowledge_and_archive_message.py --apply --workspace-root /home/agent_director_01/.nullclaw/workspace --form-file <unread_filename>`


## Runtime Notes
- Avoid unrelated shell commands; command allowlist may block them.


What the tool does:
- transitions form in DB to `ARCHIVED` via `/v1/forms/actions` (`acknowledge_message_read`)
- updates markdown frontmatter stage to `ARCHIVED`
- moves file from `inbox/unread/` to `inbox/read/`
- kernel creates a copy under master archive (`workspace/form_archive/message/<form_id>/...`)
- preflights kernel health (`/healthz`) before moving files, so connection failures do not leave partial state
- resolves actor identity from frontmatter `target` by default (or explicit `--actor-node-id` / `--actor-node-name`)
- includes compatibility fallback for older kernels: resolves `actor_node_id` via `/v1/runtime/actions` and retries if `actor_node_name` is rejected
- is idempotent for duplicate runs: if form is already in `inbox/read` with `stage: ARCHIVED`, it exits successfully.

## Validation
- Form status is `ARCHIVED` in DB.
- File frontmatter `stage` is `ARCHIVED`.
- File exists in `inbox/read/`.
- Master archive copy exists.

## Fallback
- Run the tool without `--apply` first to inspect resolved paths and payload.
