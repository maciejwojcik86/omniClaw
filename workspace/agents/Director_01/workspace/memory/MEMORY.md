# Long-term Memory

This file stores important information that should persist across sessions.

## User Information

(Important facts about the user)

## Preferences

(User preferences learned over time)

## Project Context

- Workspace automation around form processing for agent `Director_01` was exercised on 2026-03-08.
- A message form `msg_director` from `Macos_Supervisor` was successfully acknowledged and archived using the `read-and-acknowledge-internal-message` workflow.
- The archive action required explicitly supplying actor identity (`--actor-node-name Director_01`) because the script could not resolve actor node identity automatically.
- Repeated heartbeat/task runs on 2026-03-08 checked `inbox/new/` for unread forms, but the directory was consistently empty, so no forms were processed, routed, blocked, or moved to `outbox/send/`.
- `HEARTBEAT.md` contains active periodic instructions under "Check Inbox and act on tasks" for this workflow and was consulted during some of the empty-inbox checks.
- Additional repeated checks later on 2026-03-08 reconfirmed that `HEARTBEAT.md` still lists the active standing inbox-processing task and that `inbox/new/` remained empty throughout, with no file modifications or routing actions taken.
- Later on 2026-03-08, two additional unread `message` forms from `Macos_Supervisor` asking for a joke were processed for `Director_01`: `msg_debug_5-1.md` (`form_id: msg_debug_5-2`) and `msg_debug_5.md` (`form_id: msg_debug_5`). Both were handled via `read-and-acknowledge-internal-message`, archived to `inbox/read/` with `stage: ARCHIVED` and `decision: acknowledge_read`, and reply drafts were created addressed to `Macos_Supervisor`.
- During processing of `msg_debug_5-1.md`, the documented draft template path `templates/message_draft.md` was missing and no `templates/` directory was present at the workspace root, so the outgoing message had to be constructed manually using the documented frontmatter format.
- The archive script for `read-and-acknowledge-internal-message` expects a filename rather than a relative path; passing `inbox/new/msg_debug_5-1.md` failed, while rerunning with just the filename succeeded.
- Another concentrated sequence of checks between 13:59 and 14:03 on 2026-03-08 again found `inbox/new/` empty on every attempt; at 14:00, `HEARTBEAT.md` was explicitly re-read and still showed the active inbox-processing task, but there were no unread forms to process and no routing/frontmatter changes or moves to `outbox/send/`.

## Important Notes

- There is a tooling/workspace inconsistency affecting `outbox/send/`: write operations for a reply draft reported success, but subsequent reads/listings could not find the file, so persistence/visibility in `outbox/send/` is unreliable and may need investigation.
- After the one message was archived, repeated checks of `inbox/new/` showed it empty with no further unread forms to process.
- Across many repeated checks later on 2026-03-08, `inbox/new/` remained empty; no files were changed and no remediation was required.
- During the latest round of checks, the active periodic task in `HEARTBEAT.md` was reconfirmed, but there were still no actionable items because `inbox/new/` stayed empty.
- The missing `templates/message_draft.md` / absent `templates/` directory is a workspace inconsistency that can block strict adherence to the documented drafting workflow; manual construction of message drafts may be required until fixed.
- Explicit actor identity (`--actor-node-name Director_01`) remains a reliable workaround for archive-script execution in this workspace.

---

*This file is automatically updated by nanobot when important information should be remembered.*