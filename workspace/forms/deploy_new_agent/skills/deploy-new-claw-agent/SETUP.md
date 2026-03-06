# Setup: Deploy New Claw Agent Skill

This file covers first-time setup for local deploy scripts and optional privileged endpoint mode.

## 1) Nullclaw binary prerequisite (shared install)

Use one shared, root-owned binary for all agents:
- versioned binary: `/opt/omniclaw/nullclaw/<version>/nullclaw`
- stable symlink: `/opt/omniclaw/bin/nullclaw`

Install/update shared binary:

```bash
cd /home/macos/omniClaw
sudo scripts/provisioning/install_shared_nullclaw_binary.sh --apply --binary-path /abs/path/to/nullclaw
```

Quick check:

```bash
ls -la /opt/omniclaw/bin/nullclaw
/opt/omniclaw/bin/nullclaw --version
```

## 2) Sudoers allowlist for privileged helper (optional)

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

## 3) Kernel provisioning env vars (optional endpoint mode)

```bash
export OMNICLAW_PROVISIONING_MODE=system
export OMNICLAW_ALLOW_PRIVILEGED_PROVISIONING=true
export OMNICLAW_PROVISIONING_HELPER_PATH=/home/macos/omniClaw/scripts/provisioning/privileged_provisioning_helper.sh
export OMNICLAW_PROVISIONING_HELPER_USE_SUDO=true
```

## 3.1) Local deploy env vars (non-root apply mode)

The same helper env vars are also used by local deploy scripts when `--apply` runs as a non-root user:

```bash
export OMNICLAW_PROVISIONING_HELPER_PATH=/home/macos/omniClaw/scripts/provisioning/privileged_provisioning_helper.sh
export OMNICLAW_PROVISIONING_HELPER_USE_SUDO=true
```

With this enabled, `deploy_new_claw_agent.sh` can complete privileged steps (user create, binary link, config init, permission apply) through the allowlisted helper path.

## 4) Start kernel

```bash
cd /home/macos/omniClaw
uv run python main.py
```

## 4.1) Human workspace baseline inside repo

For the kernel-running human user (for example `macos`), keep a repo-local workspace:

```bash
cd /home/macos/omniClaw
uv run python scripts/provisioning/create_workspace_tree.py --apply --workspace-root /home/macos/omniClaw/workspace/macos
```

Then register that user as HUMAN node via provisioning endpoint action `register_human`.

## 5) Security notes

- Do not run the kernel service itself as root.
- Keep privileged operations constrained to the helper allowlist.
- Keep helper path fixed/immutable in runtime config.
- Keep provider credentials out of repo; inject later via secure runtime variables.

## 6) Setup-time troubleshooting

- If `sudo` cannot find `uv`, run deploy commands via `sudo env "PATH=$PATH" ...`.
- If unrestricted `sudo` is blocked, use helper-backed non-root apply mode from section `3.1`.
- For runtime/provider failures (for example `AllProvidersFailed`), follow [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

## 7) Optional manager superuser grant

For explicitly approved manager-level agents that need full host administration:

```bash
cd /home/macos/omniClaw
export OMNICLAW_PROVISIONING_HELPER_PATH=/home/macos/omniClaw/scripts/provisioning/privileged_provisioning_helper.sh
export OMNICLAW_PROVISIONING_HELPER_USE_SUDO=true
scripts/provisioning/grant_passwordless_sudo.sh --apply --username <manager_agent_username>
```
