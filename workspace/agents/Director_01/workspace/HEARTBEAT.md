# Heartbeat 

## Check Inbox and act on tasks

- Check `inbox/new/` for newly delivered form files.
- Pick one unread form and process it fully before starting another.
- Read that form's `stage_skill` value from frontmatter.
- Confirm `agent` matches your node name before editing the form.
- Open and follow the referenced skill instructions and its template.
- Append your stage response to the same `.md` form body (do not delete prior content).
- Update frontmatter for routing:
  - set a valid `decision` only when the current stage completed successfully
  - do not edit `stage` manually (kernel advances stage from workflow)
  - use `target_agent` as a read-only hint for the possible next holder per decision
  - do not change `target` unless the chosen route requires a dynamic target (for example `{{any}}` or another `{{variable}}`); in that case replace it with the concrete target required by the skill/workflow
- If the stage is blocked or failed and no valid success decision applies, append the failure notes but keep `decision` empty and leave the form in `inbox/new/` for retry or human remediation.
- When the form is ready and has a valid decision, move the edited `.md` file to `outbox/send/`.
- If a file disappears from `outbox/send/` immediately after you move it there, assume the kernel may have consumed it successfully. Check `outbox/archive/`, the next holder's inbox, or the canonical ledger before recreating or resubmitting the form.

## Heartbeat Tasks

Add tasks below that you want the agent to work on periodically.

If this file has no tasks (only headers and comments), the agent will skip the heartbeat.

### Active Tasks

<!-- Add your periodic tasks below this line -->


### Completed

<!-- Move completed tasks here or delete them -->
