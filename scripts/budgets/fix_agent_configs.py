import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.company_paths import build_company_paths
from omniclaw.config import load_settings

agents_config = {
    "HR_Head_01": {
        "model": "openrouter/minimax/minimax-01-2.5",
        "provider": "openai"
    },
    "Ops_Head_01": {
        "model": "openrouter/google/gemini-3.1-flash-lite-preview",
        "provider": "openai"
    },
    "Signal_Cartographer_01": {
        "model": "openrouter/stepfun/step-3.5-flash:free",
        "provider": "openai"
    }
}

company_paths = build_company_paths(load_settings())

for agent, config in agents_config.items():
    cfg_path = company_paths.agents_root / agent / "config.json"
    if cfg_path.exists():
        with open(cfg_path, "r") as f:
            data = json.load(f)
        
        data["agents"]["defaults"]["model"] = config["model"]
        data["agents"]["defaults"]["provider"] = config["provider"]
        
        with open(cfg_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Fixed {cfg_path}")
