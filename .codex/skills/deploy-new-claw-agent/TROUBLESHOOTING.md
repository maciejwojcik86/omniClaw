# Troubleshooting: Deploy New Claw Agent

Use this SOP when deployment or first runtime smoke test fails.

## 1) `uv: command not found` while running deploy script with `sudo`

Symptom:
- `scripts/provisioning/deploy_new_claw_agent.sh: line ...: uv: command not found`

Cause:
- `sudo` sanitizes `PATH`, so root cannot find `uv`.

Fix:

```bash
sudo env "PATH=$PATH" scripts/provisioning/deploy_new_claw_agent.sh --apply ...
```

## 2) `Permission denied` or `Workspace root ... does not exist` during non-root `--apply`

Symptom:
- `PermissionError: [Errno 13] Permission denied: '/home/<target_user>/.nullclaw/...`
- `Workspace root '/home/<target_user>/.nullclaw/workspace' does not exist`

Cause:
- `--apply` ran as non-root without helper-backed privileged path.

Fix:

```bash
export OMNICLAW_PROVISIONING_HELPER_PATH=/home/macos/omniClaw/scripts/provisioning/privileged_provisioning_helper.sh
export OMNICLAW_PROVISIONING_HELPER_USE_SUDO=true
scripts/provisioning/deploy_new_claw_agent.sh --apply ...
```

The deploy flow will route privileged steps through the allowlisted helper.

## 3) `Could not resolve shared nullclaw binary from '/opt/omniclaw/bin/nullclaw'`

Symptom:
- user-link step fails before config/workspace steps.

Cause:
- shared root binary not installed yet.

Fix:

```bash
sudo scripts/provisioning/install_shared_nullclaw_binary.sh --apply --binary-path /abs/path/to/nullclaw
```

Then re-run deploy:

```bash
sudo env "PATH=$PATH" scripts/provisioning/deploy_new_claw_agent.sh --apply --shared-nullclaw-binary /opt/omniclaw/bin/nullclaw ...
```

## 4) `AllProvidersFailed` when running `nullclaw agent -m "hello"` as target user

Symptom:
- runtime starts, then fails with provider error.

Primary checks:

```bash
sudo -u <target_user> -H bash -lc 'nullclaw status'
sudo -u <target_user> -H bash -lc 'ls -la ~/.nullclaw/config.json ~/.nullclaw/auth.json'
```

Typical cause:
- target user lacks provider auth context (`~/.nullclaw/auth.json`) even if config/model is present.

Fix for OAuth reuse from supervisor account:

```bash
sudo scripts/provisioning/sync_nullclaw_auth.sh --apply --source-user <supervisor_user> --target-user <target_user>
```

Then retry:

```bash
sudo -u <target_user> -H bash -lc 'cd ~/.nullclaw/workspace && nullclaw agent -m "hello"'
```

## 5) Verify post-fix baseline

```bash
ls -la /opt/omniclaw/bin/nullclaw
ls -la /home/<target_user>/.local/bin/nullclaw
readlink -f /home/<target_user>/.local/bin/nullclaw
sudo -u <target_user> -H bash -lc 'nullclaw --version && nullclaw status'
```

## 6) `manager_node_id or manager_node_name is required` on `provision_agent`

Symptom:
- provisioning endpoint rejects agent provisioning request with 422.

Cause:
- line management is mandatory; AGENT must have a manager node.

Fix:

1. Ensure a manager node exists (`register_human` for supervisor or existing AGENT manager).
2. Re-run `provision_agent` with one of:
   - `manager_node_id`
   - `manager_node_name`

For existing AGENT rows, use action `set_line_manager`.

## 7) `nullclaw status` shows `Heartbeat: disabled`

Symptom:
- `HOME=/home/<target_user> nullclaw status` prints `Heartbeat:   disabled`.

Cause:
- `~/.nullclaw/config.json` is missing `agents.defaults.heartbeat.every`.

Fix:

```bash
sudo -u <target_user> -H python - <<'PY'
import json
from pathlib import Path

path = Path.home() / ".nullclaw" / "config.json"
cfg = json.loads(path.read_text(encoding="utf-8"))
cfg.setdefault("agents", {}).setdefault("defaults", {}).setdefault("heartbeat", {})["every"] = "30m"
path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
PY
```

Then verify:

```bash
HOME=/home/<target_user> nullclaw status | rg -n "Heartbeat"
```

## 8) Manager agent cannot run privileged commands without password

Symptom:
- Manager agent shell reports `sudo: a password is required`.

Cause:
- User is in `sudo` group but does not have passwordless sudo policy.

Fix (approved manager accounts only):

```bash
export OMNICLAW_PROVISIONING_HELPER_PATH=/home/macos/omniClaw/scripts/provisioning/privileged_provisioning_helper.sh
export OMNICLAW_PROVISIONING_HELPER_USE_SUDO=true
scripts/provisioning/grant_passwordless_sudo.sh --apply --username <manager_agent_username>
```
