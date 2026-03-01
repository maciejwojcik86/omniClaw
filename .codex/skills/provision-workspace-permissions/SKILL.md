---
name: provision-workspace-permissions
description: Apply owner/group access policy for one workspace as a standalone step after scaffold creation.
license: MIT
compatibility: Linux host with `chown`, `chmod`, and `find`; apply mode requires root/sudo.
metadata:
  author: omniclaw
  version: "0.1"
---

Provision exactly one concern: ownership and manager-group access.

Use this skill after workspace scaffold exists. Do not create Linux users in this step.

## Inputs

- `owner_user` (required)
- `manager_group` (required)
- `workspace_root` (required)

## Steps

1. Preview commands:
   - `scripts/provisioning/apply_workspace_permissions.sh --owner-user <owner> --manager-group <group> --workspace-root <path>`
2. Apply policy:
   - `scripts/provisioning/apply_workspace_permissions.sh --apply --owner-user <owner> --manager-group <group> --workspace-root <path>`
3. Verify:
   - `stat -c '%U:%G %A %n' <workspace_root>`
   - `find <workspace_root> -maxdepth 2 -type d -exec stat -c '%U:%G %A %n' {} \;`

## Kernel endpoint fallback

If no privilege is available, call the kernel privileged API:
- `scripts/provisioning/trigger_kernel_action.sh --payload-file <json-file>`

Example payload:
```json
{
  "action": "apply_workspace_permissions",
  "owner_user": "agent_director_01",
  "manager_group": "sudo",
  "workspace_root": "/home/agent_director_01/workspace"
}
```

## Output contract

Return concise status with:
- owner/group applied
- permission mode summary
- directories updated
