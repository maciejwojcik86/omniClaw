---
name: provision-linux-user
description: Create or verify one Linux user for an OmniClaw agent as a standalone, testable provisioning step.
license: MIT
compatibility: Linux host with `useradd`; apply mode requires root/sudo.
metadata:
  author: omniclaw
  version: "0.1"
---

Provision exactly one concern: Linux user identity.

Use this skill when you need to create a new agent user without coupling it to workspace scaffolding or permission policy.

## Inputs

- `username` (required)
- `home_dir` (optional, defaults to `/home/<username>`)
- `uid` (optional)
- `shell` (optional, defaults to `/usr/sbin/nologin`)

## Steps

1. Validate target user does not already exist (or treat existing user as idempotent success).
2. Run helper script in dry-run mode first:
   - `scripts/provisioning/create_linux_user.sh --username <username> [--home-dir ...] [--uid ...] [--shell ...]`
3. Execute apply mode only after dry-run output is reviewed:
   - `scripts/provisioning/create_linux_user.sh --apply --username <username> ...`
4. Verify:
   - `id <username>`
   - `getent passwd <username>`

## Kernel endpoint fallback

If the current environment cannot run privileged host commands, send the request to a kernel endpoint:
- `scripts/provisioning/trigger_kernel_action.sh --payload-file <json-file>`

Example payload:
```json
{
  "action": "create_linux_user",
  "username": "agent_director_01",
  "home_dir": "/home/agent_director_01",
  "shell": "/bin/bash",
  "groups": ["sudo"]
}
```

## Output contract

Return concise status with:
- whether user was created or already existed
- resolved home directory
- resolved shell
