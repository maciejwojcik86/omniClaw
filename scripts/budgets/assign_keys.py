#!/usr/bin/env python3
import json
import uuid
from decimal import Decimal
from pathlib import Path

from omniclaw.config import load_settings
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_session_factory

def run() -> None:
    settings = load_settings()
    session_factory = create_session_factory(settings.database_url)
    repo = KernelRepository(session_factory)
    
    nodes = repo.list_active_agent_nodes_with_workspaces()
    if not nodes:
        print("No active agents found.")
        return

    # User provided an open router api key with $4 budget to be assigned evenly
    total_budget_usd = 4.0
    num_agents = len(nodes)
    budget_per_agent = total_budget_usd / num_agents

    for node in nodes:
        print(f"Processing agent {node.name}...")

        virtual_key = f"sk-virtual-{uuid.uuid4().hex}"
        
        # Upsert into OmniClaw DB
        budget = repo.upsert_budget(
            node_id=node.id, 
            virtual_api_key=virtual_key, 
            daily_limit_usd=Decimal(str(budget_per_agent))
        )
        print(f" -> Saved to DB: Key={virtual_key[:16]}... Budget=${budget.daily_limit_usd:.2f}")

        # Update the config.json for the agent
        config_path = Path(node.runtime_config_path)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # Setup liteLLM base and key in agent config
            if "agents" not in config:
                config["agents"] = {}
            if "defaults" not in config["agents"]:
                config["agents"]["defaults"] = {}
            if "providers" not in config:
                config["providers"] = {}
            if "custom" not in config["providers"]:
                config["providers"]["custom"] = {}
            
            # Using standard litellm port 4000
            config["agents"]["defaults"]["model"] = "openrouter/openai/gpt-4o"
            config["agents"]["defaults"]["provider"] = "custom"
            config["providers"]["custom"]["apiBase"] = "http://localhost:4000"
            config["providers"]["custom"]["apiKey"] = virtual_key
            config["agents"]["defaults"].pop("apiBase", None)
            config["agents"]["defaults"].pop("apiKey", None)
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            print(f" -> Updated config at {config_path}")
        else:
            print(f" -> Warning: config.json missing at {config_path}")

if __name__ == "__main__":
    run()
