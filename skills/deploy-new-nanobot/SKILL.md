---
name: deploy-new-nanobot
description: Provision a repo-local Nanobot agent directory, register the AGENT node, write workspace instructions, and verify the Nanobot runtime contract.
---

Use this skill when you need to deploy or revise a canonical OmniClaw AGENT backed by Nanobot.

## Scope

- Provision AGENT nodes under `workspace/agents/<agent_name>/`
- Create or update sibling `config.json`
- Create or update `workspace/` scaffold and `AGENTS.md`
- Use the canonical baseline files from `workspace/nanobot_workspace_templates/`
- Preserve the delivered inbox contract as `inbox/new`
- Verify manual Nanobot smoke commands
- Capture reusable deployment evidence for the deploy workflow

## Inputs

- `node_name` (required)
- `manager_node_id` or `manager_node_name` (required)
- optional `username` as legacy metadata only
- optional `workspace_root`, `runtime_config_path`, `primary_model`, `autonomy_level`
- optional custom `AGENTS.md` source file

## Steps

1. Confirm Nanobot CLI contract:
   - `nanobot gateway --help`
   - `nanobot agent --help`
2. Dry-run provisioning:
   - `scripts/provisioning/deploy_new_nanobot_agent.sh --node-name <agent_name> --manager-node-name <manager>`
3. Apply provisioning:
   - `scripts/provisioning/deploy_new_nanobot_agent.sh --apply --node-name <agent_name> --manager-node-name <manager>`
4. Verify created assets:
   - `find workspace/agents/<agent_name> -maxdepth 2 | sort`
   - `cat workspace/agents/<agent_name>/config.json`
   - `find workspace/agents/<agent_name>/workspace/inbox -maxdepth 1 -type d | sort`
5. Smoke the local CLI agent:
   - `nanobot agent -w workspace/agents/<agent_name>/workspace -c workspace/agents/<agent_name>/config.json -m "Hello"`
6. If gateway smoke is needed, use a unique port:
   - `nanobot gateway -w workspace/agents/<agent_name>/workspace -c workspace/agents/<agent_name>/config.json -p 18793`

## Verification

- `uv run pytest tests/test_provisioning_actions.py tests/test_runtime_actions.py -q`
- `uv run pytest tests/test_nanobot_skill_wrappers.py -q`
- `uv run python scripts/provisioning/list_agents_permissions.py --database workspace/omniclaw.db`
- confirm the node row has `workspace_root` and `runtime_config_path`

## Fallback

- If the deploy script fails, submit the same payload through `scripts/provisioning/trigger_kernel_action.sh`.
- If the workspace exists but instructions are stale, rerun `scripts/provisioning/write_agent_instructions.py --apply`.
- If Nanobot is missing on the host, install from `/home/macos/nanobot` with `python3 -m pip install -e .`.
