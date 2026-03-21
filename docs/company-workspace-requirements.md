# Company Workspace Requirements

OmniClaw now supports exactly one runtime workspace per company, defined by that company's `workspace_root` in `~/.omniClaw/config.json`.

There is no repo-local runtime workspace fallback.
There is no bootstrap requirement.
There is no migration helper requirement.
If the configured company workspace is missing required assets, OmniClaw should fail loudly instead of reading from another location.

## Source of Truth

For a company entry like:

```json
{
  "companies": {
    "omniclaw": {
      "workspace_root": "/home/macos/.omniClaw/workspace"
    }
  }
}
```

OmniClaw treats that `workspace_root` as the only valid company workspace.

## Required Top-Level Structure

A correctly configured company workspace must contain these top-level paths:

- `agents/`
- `forms/`
- `master_skills/`
- `nanobots_instructions/`
- `nanobot_workspace_templates/`
- `form_archive/`
- `logs/`
- `retired/`
- `runtime_packages/`
- `finances/`
- `NEW_INBOX_MESSAGE_PROMPT.md`
- `omniclaw.db`

## Required Runtime Assets

### 1. Forms

`forms/` contains the active workflow packages used by the kernel.

Expected shape:

- `forms/<form_type>/workflow.json`
- `forms/<form_type>/skills/<required_skill>/SKILL.md`

Example:

- `forms/message/workflow.json`
- `forms/message/skills/read-and-acknowledge-internal-message/SKILL.md`

### 2. Master Skills

`master_skills/` contains loose company skills that can be cataloged and assigned.

Expected shape:

- `master_skills/<skill_name>/SKILL.md`
- optional `master_skills/<skill_name>/skill.json`

### 3. Instruction Templates

`nanobots_instructions/` contains per-node instruction templates used by the instructions service.

Expected shape:

- `nanobots_instructions/<node_name>/AGENTS.md`

### 4. Workspace Templates

`nanobot_workspace_templates/` contains the baseline files used when agent workspaces are scaffolded.

Expected minimum files:

- `AGENTS.md`
- `AGENTS.placeholder.md`
- `HEARTBEAT.md`
- `SOUL.md`
- `USER.md`
- `TOOLS.md`
- `config.json`
- `memory/MEMORY.md`
- `memory/HISTORY.md`
- `notes/DECISIONS.md`
- `notes/BLOCKERS.md`
- `metrics/KPI.csv`

### 5. Inbox Wake Prompt

`NEW_INBOX_MESSAGE_PROMPT.md` is the company-level prompt rendered after IPC delivers a new form into an AGENT inbox.

Supported placeholders:

- `{{agent_name}}`
- `{{sender_name}}`
- `{{form_id}}`
- `{{form_type}}`
- `{{stage}}`
- `{{stage_skill}}`
- `{{subject}}`
- `{{delivery_path}}`
- `{{archive_path}}`
- `{{target_agent}}`

## Failure Semantics

OmniClaw should fail instead of silently falling back when any of these are missing:

- company `forms/`
- company `master_skills/`
- company `nanobot_workspace_templates/`
- required template files such as `nanobot_workspace_templates/AGENTS.md`

This is intentional: one configured company workspace must be the only source of truth.

## Operational Rule

If you need to change company assets:
- edit the configured company workspace directly
- do not edit a repo-local `workspace/` copy
- do not rely on hidden fallback behavior

## Current Local Developer Example

For the local developer environment in this repo, the active company workspace is:

- `/home/macos/.omniClaw/workspace`

That path, as referenced by `~/.omniClaw/config.json`, is the only intended runtime workspace for the `omniclaw` company.
