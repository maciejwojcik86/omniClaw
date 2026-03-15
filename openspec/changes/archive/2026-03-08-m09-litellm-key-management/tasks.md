## 1. Setup LiteLLM Client & Models

- [x] 1.1 Add `LITELLM_MASTER_KEY` and `LITELLM_PROXY_URL` to OmniClaw configuration (`config.py`).
- [x] 1.2 Create `src/omniclaw/litellm_client.py` wrapper for `/key/generate` and `/user/info` calls.

## 2. Provisioning & Config Template Integration

- [x] 2.1 Modify `deploy_new_agent` provisioning flow to call `LiteLLMClient.generate_virtual_key()`.
- [x] 2.2 Save `virtual_api_key` to the `budgets` table for the target node.
- [x] 2.3 Inject the LiteLLM proxy URL (`apiBase`) and generated Virtual Key (`apiKey`) into the agent's `config.json` via workspace templating.

## 3. Cost Ingestion Pipeline

- [x] 3.1 Add backend endpoint/service (`src/omniclaw/budgets/`) to query LiteLLM `/user/info` for tracked agents.
- [x] 3.2 Update `budgets.current_spend` and `daily_limit_usd` based on LiteLLM proxy response.
- [x] 3.3 Add endpoint to adjust proxy `max_budget` for a given agent via LiteLLM `/user/update`.

## 4. Automation & Skills

- [x] 4.1 Author `manage-agent-budgets` operational skill documenting how to review agent allocations, usages, and extend allowances or cross-compare agents via scripts or endpoints.
- [x] 4.2 Run tests, update repository mappings, and pass OpenSpec `strict` validation.r reviewing and extending allowances.
- [ ] 4.3 Verify end-to-end local deployment flow (run provisioning script).
