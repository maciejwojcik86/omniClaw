# Troubleshooting: Nullclaw Runtime

## `AllProvidersFailed` during `nullclaw agent`

Symptom:
- `nullclaw agent -m "hello"` fails with `AllProvidersFailed`.

Checklist:

```bash
nullclaw status
nullclaw channel status
ls -la ~/.nullclaw/config.json ~/.nullclaw/auth.json
```

Common causes:
- default model configured but no usable auth/token context for that provider.
- missing or unreadable `~/.nullclaw/auth.json` for the runtime user.

Fix pattern for OmniClaw-managed users:
1. Ensure config points to expected model/provider.
2. Ensure target user has auth context.
3. Retry agent smoke command under target user.

Example auth sync (run as privileged operator):

```bash
sudo /home/macos/omniClaw/scripts/provisioning/sync_nullclaw_auth.sh --apply --source-user <supervisor_user> --target-user <agent_user>
```

Retry:

```bash
sudo -u <agent_user> -H bash -lc 'cd ~/.nullclaw/workspace && nullclaw agent -m "hello"'
```

## Runtime context mismatch

Symptom:
- command works as one user but fails as another.

Cause:
- each Linux user has separate `~/.nullclaw` auth/config state.

Fix:
- always validate and run smoke tests under the exact target runtime user:

```bash
sudo -u <agent_user> -H bash -lc 'nullclaw --version && nullclaw status'
```
