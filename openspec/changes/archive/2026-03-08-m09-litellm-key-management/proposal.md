## Why

To support strict waterfall budgets and robust cost tracking, we must persist API keys and usage costs. Since LiteLLM supports virtual key generation and per-key/user tracking, we need to associate each OmniClaw Agent node with a LiteLLM virtual key and ingest their proxy usage to enable the M10 budget engine.

## What Changes

- Add schema fields for tracking LiteLLM virtual keys (e.g., `litellm_user_id`, `litellm_virtual_key`) on `nodes`.
- Introduce a service to generate LiteLLM virtual keys per agent.
- Add an ingestion job/daemon to pull spend data from LiteLLM proxy and persist to a daily or per-node cost tracking table.
- Create operational tools (skills) and operator endpoints to monitor usage, allocate budgets, and manage keys.
- **BREAKING**: No breaking changes expected initially, but operators must provide a master LiteLLM key in the environment to provision new agents.

## Capabilities

### New Capabilities
- `litellm-integration`: Managing LiteLLM virtual keys and ingesting cost/usage.
- `budget-management`: Budget operations, allowance adjustments, cross-comparison.

### Modified Capabilities
- `agent-runtime-bootstrap`: Needs to be updated so that the generated nanobot config injects the virtual key and proxy endpoint URL.

## Impact

- `nodes` schema and migration: Adding fields for LiteLLM identity.
- New `agent_costs` or similar table: Tracking daily spend per node.
- `omniclaw.provisioning` service: Now interacts with LiteLLM proxy to issue a key during `deploy_new_agent` workflow.
- Nanobot workspace config generation: Templating the `apiBase` and `apiKey` to route through the proxy.
- External dependency: `LITELLM_MASTER_KEY` and Proxy URL must be available to the Kernel.
