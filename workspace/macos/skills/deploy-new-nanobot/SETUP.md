# Setup: Deploy New Nanobot Skill

This file covers first-time setup for the Nanobot deploy scripts and the optional packaging path for the vendored monorepo Nanobot fork.

## 1) Nanobot CLI prerequisite

Confirm Nanobot is installed and the tested multi-instance flags are available:

```bash
nanobot --help
nanobot gateway --help
nanobot agent --help
```

Expected commands used by OmniClaw:

```bash
nanobot gateway -w <workspace_root> -c <config_path> -p <port>
nanobot agent -w <workspace_root> -c <config_path>
nanobot agent -w <workspace_root> -c <config_path> -m "hello"
```

## 2) Install path options

Official install:

```bash
uv tool install nanobot-ai
```

Vendored monorepo fork path (recommended when you need the OmniClaw-specific Nanobot customizations):

```bash
cd /home/macos/omniClaw
workspace/forms/deploy_new_agent/skills/deploy-new-nanobot/scripts/package_nanobot_source.sh --apply --source-dir /home/macos/omniClaw/third_party/nanobot --output-dir /home/macos/omniClaw/workspace/runtime_packages
```

On another machine:

```bash
tar -xzf nanobot-custom-<timestamp>.tar.gz
pip install /path/to/unpacked/nanobot
```

## 3) Provider authentication

If the selected model uses the Codex OAuth provider, authenticate once on the host:

```bash
nanobot provider login openai-codex
```

If the selected provider uses API keys instead, add them to the deployed `config.json` before runtime smoke.

## 4) Start the kernel

```bash
cd /home/macos/omniClaw
uv run omniclaw
```

## 5) Human workspace baseline inside repo

For the kernel-running human user (for example `macos`), keep a repo-local workspace:

```bash
cd /home/macos/omniClaw
python3 workspace/forms/deploy_new_agent/skills/deploy-new-nanobot/scripts/create_workspace_tree.py --apply --workspace-root /home/macos/omniClaw/workspace/macos
```

Then register that user as a HUMAN node with the provisioning endpoint action `register_human`.

## 6) Security notes

- Do not run the kernel service itself as root.
- Keep the canonical standard templates under `/home/macos/omniClaw/workspace/nanobot_workspace_templates/`.
- Use `tools.restrictToWorkspace=false` for deployed OmniClaw agents because deployment and workflow operations need repo-local access outside a single agent workspace.
- Keep AGENT runtimes in repo-local `workspace/agents/<agent_name>/` directories.
- Keep provider credentials out of git-tracked files; inject them after provisioning.

## 7) Setup-time troubleshooting

- If `nanobot` is missing from `PATH`, install it before using this skill.
- If the packaged fork is required on another host, install from the archived vendored source instead of PyPI.
- For runtime/provider failures, follow [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).
