# Troubleshooting: Deploy New Nanobot

Use this SOP when deployment or first runtime smoke test fails.

## 1) `nanobot: command not found`

Symptom:
- `nanobot: command not found`

Cause:
- Nanobot is not installed on the host or is missing from `PATH`.

Fix:

```bash
uv tool install nanobot-ai
```

Or install your packaged local fork:

```bash
tar -xzf nanobot-custom-<timestamp>.tar.gz
pip install /path/to/unpacked/nanobot
```

## 2) Runtime starts in the wrong workspace

Symptom:
- Nanobot reads the default `~/.nanobot/workspace` instead of the deployed OmniClaw agent workspace.

Cause:
- `gateway` or `agent` was launched without both `-w` and `-c`, or `config.json` still points at the old workspace.

Fix:

```bash
python3 skills/deploy-new-nanobot/scripts/init_nanobot_config.py --apply --workspace-root /home/macos/omniClaw/workspace/agents/<agent_name>/workspace --config-path /home/macos/omniClaw/workspace/agents/<agent_name>/config.json
nanobot gateway -w /home/macos/omniClaw/workspace/agents/<agent_name>/workspace -c /home/macos/omniClaw/workspace/agents/<agent_name>/config.json -p 18790
```

## 3) Provider authentication fails

Symptom:
- `nanobot agent -m "hello"` fails with a provider/auth error.

Primary checks:

```bash
ls -la /home/macos/omniClaw/workspace/agents/<agent_name>/config.json
nanobot provider login openai-codex
```

Typical cause:
- The deployed config has a model but the host has not been authenticated for that provider yet.

Fix:
- Run `nanobot provider login openai-codex` for Codex OAuth.
- Or add the required API key under the deployed `config.json` provider section.

## 4) `nanobot status` does not describe the deployed agent instance

Symptom:
- `nanobot status` shows the default Nanobot home instance rather than the deployed agent you just provisioned.

Cause:
- Current `status` uses the default config/workspace instead of explicit `-w/-c` overrides.

Fix:
- Use the explicit runtime commands for the target instance:

```bash
nanobot gateway -w /home/macos/omniClaw/workspace/agents/<agent_name>/workspace -c /home/macos/omniClaw/workspace/agents/<agent_name>/config.json -p 18790
nanobot agent -w /home/macos/omniClaw/workspace/agents/<agent_name>/workspace -c /home/macos/omniClaw/workspace/agents/<agent_name>/config.json -m "hello"
```

- For kernel-managed runtime state, inspect the runtime endpoint response and the workspace `drafts/runtime/` artifacts.

## 5) `manager_node_id or manager_node_name is required` on `provision_agent`

Symptom:
- The provisioning endpoint rejects the agent provisioning request with HTTP 422.

Cause:
- Line management is still mandatory; every AGENT must have a manager node.

Fix:

1. Ensure a manager node exists (`register_human` for a supervisor or an existing AGENT manager).
2. Re-run `provision_agent` with one of:
   - `manager_node_id`
   - `manager_node_name`

For existing AGENT rows, use the `set_line_manager` action.

## 6) `runtime config does not exist` or workspace root is missing

Symptom:
- Runtime start fails because the configured `config.json` or workspace path is missing.

Fix:

```bash
python3 skills/deploy-new-nanobot/scripts/create_workspace_tree.py --apply --workspace-root /home/macos/omniClaw/workspace/agents/<agent_name>/workspace
python3 skills/deploy-new-nanobot/scripts/init_nanobot_config.py --apply --workspace-root /home/macos/omniClaw/workspace/agents/<agent_name>/workspace --config-path /home/macos/omniClaw/workspace/agents/<agent_name>/config.json
```

## 7) Gateway port already in use

Symptom:
- `nanobot gateway ... -p <port>` fails to start because the port is bound.

Fix:
- Pick a different port for the agent instance.
- Update both the launch command and the agent `config.json` gateway port if you want the config to stay canonical.

## 8) Standard template files are missing or drifted

Symptom:
- Workspace scaffold or config generation fails because `workspace/agent_templates/*` is missing or stale.

Cause:
- The deploy skill and kernel scaffold both load standard files from `/home/macos/omniClaw/workspace/agent_templates/`.

Fix:
- Restore the expected files under `/home/macos/omniClaw/workspace/agent_templates/`.
- Re-run `skills/deploy-new-nanobot/scripts/create_workspace_tree.py` and `skills/deploy-new-nanobot/scripts/init_nanobot_config.py` after the templates are corrected.
