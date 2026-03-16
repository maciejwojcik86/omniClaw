# Nanobot Monorepo Ops

## Scope
- Maintain the vendored `third_party/nanobot/` runtime package inside the OmniClaw monorepo.
- Bootstrap the shared environment that exposes both `omniclaw` and `nanobot`.
- Verify prompt-log and usage persistence against a registered OmniClaw company.

## Required Inputs
- Repo root: `/home/macos/omniClaw`
- Registered company slug or display name, for example `omniclaw`
- Deployed agent name for prompt-log checks

## Canonical Paths
- Vendored Nanobot source: `third_party/nanobot/`
- Monorepo bootstrap installer: `scripts/install/bootstrap_monorepo.sh`
- Prompt-log helper: `scripts/runtime/list_prompt_logs.py`
- Optional company-context helper: `scripts/company/show_company_context.py`

## Execution Steps
1. Refresh the shared environment:
   - `bash scripts/install/bootstrap_monorepo.sh`
2. Verify both CLI entrypoints resolve:
   - `uv run omniclaw --help`
   - `uv run nanobot --help`
3. Run the OmniClaw monorepo test suite:
   - `uv run pytest -q tests`
4. Start the kernel from the packaged CLI path:
   - `bash scripts/runtime/start_local_stack.sh --company omniclaw`
5. Run a kernel-managed prompt:
   - `bash scripts/runtime/invoke_agent_prompt.sh --apply --node-name <agent_name> --prompt "Reply with exactly: pong" --session-key cli:m12-monorepo`
6. Inspect prompt artifacts:
   - `uv run python scripts/runtime/list_prompt_logs.py --company omniclaw --agent-name <agent_name> --limit 5`
   - `find "$HOME/.omniClaw/workspace/agents/<agent_name>/workspace/drafts/runtime/prompt_logs" -type f | sort | tail`
7. Confirm usage persistence:
   - `bash scripts/usage/get_session_summary.sh --apply --session-key cli:m12-monorepo`

## Verification
- `uv sync` resolves `nanobot-ai` from `third_party/nanobot/`.
- `omniclaw` and `nanobot` both run from the shared environment.
- Prompt-log JSON files land under `drafts/runtime/prompt_logs/` for OmniClaw-managed calls.
- Prompt-log payloads exclude API keys and transport headers.

## Fallback
- If `nanobot` is missing, rerun `bash scripts/install/bootstrap_monorepo.sh`.
- If prompt logs are missing, confirm the agent was invoked through OmniClaw-managed runtime paths.
- If the company cannot be resolved, inspect `~/.omniClaw/config.json` with `scripts/company/show_company_context.py`.
