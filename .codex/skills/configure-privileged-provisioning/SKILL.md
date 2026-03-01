---
name: configure-privileged-provisioning
description: Configure a narrow privileged execution path for provisioning actions without running the whole kernel as root.
license: MIT
compatibility: Linux with sudoers access
metadata:
  author: omniclaw
  version: "0.1"
---

Use this skill to allow `/v1/provisioning/actions` system-mode calls to execute privileged host actions safely.

## Goal

Grant the kernel process access only to one helper entrypoint:
- `scripts/provisioning/privileged_provisioning_helper.sh`

## Steps

1. Ensure helper exists and is executable:
   - `ls -l scripts/provisioning/privileged_provisioning_helper.sh`
2. Add sudoers rule for the kernel service user (example user: `omniclaw`):
   - `omniclaw ALL=(root) NOPASSWD: /home/macos/omniClaw/scripts/provisioning/privileged_provisioning_helper.sh *`
3. Export runtime env for kernel service:
   - `OMNICLAW_PROVISIONING_MODE=system`
   - `OMNICLAW_ALLOW_PRIVILEGED_PROVISIONING=true`
   - `OMNICLAW_PROVISIONING_HELPER_PATH=/home/macos/omniClaw/scripts/provisioning/privileged_provisioning_helper.sh`
   - `OMNICLAW_PROVISIONING_HELPER_USE_SUDO=true`
4. Restart kernel service.
5. Verify endpoint path with dry-run-style payload in a safe environment first.

## Notes

- Do not grant unrestricted sudo privileges to the kernel process.
- Keep privileged operations behind helper action allowlist.
- Keep filesystem ownership/permission policy in OpenSpec scope.
