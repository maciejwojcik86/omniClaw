# Setup: Provision Agent Workspace Skill

This file contains first-time setup for privileged provisioning via kernel endpoint.

## 1) Sudoers allowlist for helper

Add a narrow allowlist entry:

```bash
sudo visudo -f /etc/sudoers.d/omniclaw-provisioning
```

Content:

```text
<kernel-user> ALL=(root) NOPASSWD: /home/macos/omniClaw/scripts/provisioning/privileged_provisioning_helper.sh *
```

Set permissions:

```bash
sudo chmod 440 /etc/sudoers.d/omniclaw-provisioning
sudo visudo -cf /etc/sudoers.d/omniclaw-provisioning
```

## 2) Kernel provisioning env vars

```bash
export OMNICLAW_PROVISIONING_MODE=system
export OMNICLAW_ALLOW_PRIVILEGED_PROVISIONING=true
export OMNICLAW_PROVISIONING_HELPER_PATH=/home/macos/omniClaw/scripts/provisioning/privileged_provisioning_helper.sh
export OMNICLAW_PROVISIONING_HELPER_USE_SUDO=true
```

## 3) Start kernel

```bash
cd /home/macos/omniClaw
uv run python main.py
```

## 4) Security notes

- Do not run the entire kernel service as root.
- Keep privileged actions limited to the helper allowlist.
- Keep helper path fixed and immutable in service config.
