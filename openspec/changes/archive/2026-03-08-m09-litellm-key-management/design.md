## Context

OmniClaw agents require usage tracking and hard budget enforcement to prevent runaway LLM costs. LiteLLM proxy provides virtual keys, rate limiting, and cost tracking out-of-the-box. We will integrate LiteLLM virtual key provisioning and cost ingestion directly into the OmniClaw Kernel to enforce the financial governance model.

## Goals / Non-Goals

**Goals:**
- Automatically provision unique LiteLLM virtual keys whenever an agent is deployed (or missing a key).
- Provide a mechanism to ingest and track the proxy's `current_spend` for each agent inside the OmniClaw SQLite DB.
- Inject the proxy URL and virtual key into the Nanobot `config.json` at provision time.

**Non-Goals:**
- Deploying the LiteLLM proxy container itself (this is assumed to be running and its `MASTER_KEY` / `URL` provided via environment block).

## Decisions

1. **LiteLLM Key Provisioning at Deploy Time**
   - *Decision*: Modify `deploy_new_agent` provisioning pipeline in `omniclaw.provisioning` to call the LiteLLM proxy `/key/generate` endpoint, associating the key with the node's `id` as `user_id`.
   - *Rationale*: A 1:1 mapping between `node_id` and LiteLLM `user_id` makes tracking usage simple. The virtual key is stored in the `budgets.virtual_api_key` field.
   - *Alternative*: Share a single proxy key and rely solely on `user=` parameter in chat requests. Rejected because virtual keys offer strict, proxy-enforced budget limits which is more deterministic.

2. **Cost Ingestion Sync**
   - *Decision*: Create an endpoint/daemon capability that pings LiteLLM `/user/info` for each tracked node and updates `budgets.current_spend`.
   - *Rationale*: Keeps OmniClaw deterministic rules in control, but relies on LiteLLM for the actual dollar-value math.
   - *Alternative*: Calculate tokens directly from proxy logs. Rejected due to complexity.

3. **Nanobot Configuration**
   - *Decision*: In `omniclaw.provisioning.agent_workspace`, write the `apiBase` pointing to the LiteLLM proxy and the generated `apiKey` into the `config.json`.
   - *Rationale*: Completely decouples Nanobot from actual LLM credentials.

## Risks / Trade-offs

- **Risk: LiteLLM Proxy Downtime** → *Mitigation*: The provisioning logic must handle proxy errors gracefully and retry.
- **Risk: Budget Drift** → *Mitigation*: The proxy enforces limits in real-time. OmniClaw's ingestion just mirrors it for internal dashboarding and manager approvals.

## Migration Plan
- No schema migration needed as `Budget` table already exists with `virtual_api_key` and `current_spend`. If required, we might add a `litellm_user_id` field if `node.id` is not sufficient, but we can just use `node.id`.
