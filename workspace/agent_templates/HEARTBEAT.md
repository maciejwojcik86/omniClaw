# Heartbeat

## Check Inbox and act on tasks

- Check `inbox/unread/` for unread form files.
- Pick one unread form and process it fully before starting another.
- Read that form's `stage_skill` value from frontmatter.
- Open and follow the referenced skill instructions and its template.
- Append your stage response to the same `.md` form body (do not delete prior content).
- Update frontmatter for routing:
  - set a valid `decision` only when the current stage completed successfully
  - do not edit `stage` manually (kernel advances stage from workflow)
  - do not change `target` unless the next stage uses a dynamic target (for example `{{any}}` or another `{{variable}}`); in that case set the concrete target field required by the skill/workflow
- If the stage is blocked or failed and no valid success decision applies, append the failure notes but keep `decision` empty and leave the form in `inbox/unread/` for retry or human remediation.
- When the form is ready and has a valid decision, move the edited `.md` file to `outbox/pending/`.
- If a file disappears from `outbox/pending/` immediately after you move it there, assume the kernel may have consumed it successfully. Check `outbox/archive/`, the next holder's inbox, or the canonical ledger before recreating or resubmitting the form.
