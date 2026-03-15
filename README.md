## Start the kernel

To start the OmniClaw daemon app (which includes the IPC router and the context injector)

uv run python main.py

If `.env` points `LITELLM_PROXY_URL` at `localhost` or `127.0.0.1`, `main.py`
will also start the local LiteLLM proxy automatically.

to check if the kernel daemon is already running is by hitting its built-in health endpoint using curl

curl -s http://localhost:8000/healthz


## Budget

bash scripts/budgets/trigger_budget_action.sh --apply --action team_budget_view --node-name HR_Head_01

## Running each bot 

nanobot agent -w workspace/agents/<agent_name>/workspace -c workspace/agents/<agent_name>/config.json -m "Hello"

### Director_01
nanobot agent -w workspace/agents/Director_01/workspace -c workspace/agents/Director_01/config.json

### HR_Head_01
nanobot agent -w workspace/agents/HR_Head_01/workspace -c workspace/agents/HR_Head_01/config.json

### Ops_Head_01
nanobot agent -w workspace/agents/Ops_Head_01/workspace -c workspace/agents/Ops_Head_01/config.json

### Signal_Cartographer_01
nanobot agent -w workspace/agents/Signal_Cartographer_01/workspace -c workspace/agents/Signal_Cartographer_01/config.json
