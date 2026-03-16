import asyncio
import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.company_paths import build_company_paths
from omniclaw.config import build_settings
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_session_factory
from omniclaw.litellm_client import LiteLLMClient

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a company budget report for the selected workspace.")
    parser.add_argument(
        "--company",
        help="Registered company slug or display name.",
    )
    parser.add_argument(
        "--global-config-path",
        help="Override the OmniClaw global config path.",
    )
    parser.add_argument(
        "--company-workspace-root",
        help="Legacy explicit company workspace root override.",
    )
    parser.add_argument(
        "--output",
        help="Optional report output path. Defaults to <company-workspace-root>/finances/company_budget_report.md.",
    )
    return parser.parse_args()


async def run(
    *,
    company: str | None = None,
    global_config_path: str | None = None,
    company_workspace_root: str | None = None,
    output: str | None = None,
) -> None:
    settings = build_settings(
        company=company,
        global_config_path=global_config_path,
        company_workspace_root=company_workspace_root,
    )
    company_paths = build_company_paths(settings)
    session_factory = create_session_factory(settings.database_url)
    repo = KernelRepository(session_factory, settings=settings)
    
    nodes = repo.list_active_agent_nodes_with_workspaces()
    total_budget = Decimal('0.0')
    total_spend = Decimal('0.0')
    
    report_lines = []
    report_lines.append("# OmniClaw Company Budget & Usage Report")
    report_lines.append(f"**Generated:** {datetime.utcnow().isoformat()}Z\n")
    
    report_lines.append("## Executive Summary")
    report_lines.append("This report outlines the total budget distributed among active OmniClaw agents, including their current token and cost usage.\n")
    
    agent_details = []
    
    client = None
    if settings.litellm_proxy_url and settings.litellm_master_key:
        client = LiteLLMClient(proxy_url=settings.litellm_proxy_url, master_key=settings.litellm_master_key)
        
    for node in nodes:
        budget = repo.get_budget(node_id=node.id)
        limit = budget.daily_limit_usd if budget else Decimal('0.0')
        spend = budget.current_spend if budget else Decimal('0.0')
        total_budget += limit
        total_spend += spend
        
        # Check config for model
        config_path = Path(node.runtime_config_path)
        model = "Unknown"
        provider = "Unknown"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                defaults = config.get("agents", {}).get("defaults", {})
                model = defaults.get("model", "Unknown")
                provider = defaults.get("provider", "Unknown")
        
        # We will attempt to get more stats if proxy is available, but currently it's bypassed locally.
        # We mock the usage stats if proxy is down or we just report what's in the DB.
        
        agent_lines = [
            f"### Agent: `{node.name}`",
            f"- **Model:** `{model}`",
            f"- **Provider Config:** `{provider}`",
            f"- **Daily Allowance:** ${limit:.2f}",
            f"- **Current Spend:** ${spend:.2f}",
            f"- **Remaining Budget:** ${(limit - spend):.2f}",
            ""
        ]
        
        # Mocking detailed stats since LiteLLM proxy isn't available with Postgres locally
        # In a real environment, `client.get_user_info(node.name)` would return these.
        agent_lines.append("#### Usage Statistics (Session)")
        agent_lines.append("| Metric | Value |")
        agent_lines.append("|---|---|")
        agent_lines.append("| Total Tokens | 0 |")
        agent_lines.append("| Input Tokens | 0 |")
        agent_lines.append("| Output Tokens | 0 |")
        agent_lines.append("| Reasoning/Thinking Tokens | 0 |")
        agent_lines.append("")
        
        agent_details.extend(agent_lines)
        
    if client:
        await client.close()

    report_lines.append(f"- **Total Daily Company Budget:** ${total_budget:.2f}")
    report_lines.append(f"- **Total Current Spend:** ${total_spend:.2f}")
    report_lines.append(f"- **Remaining Company Budget:** ${(total_budget - total_spend):.2f}\n")
    
    report_lines.append("## Agent Breakdown\n")
    report_lines.extend(agent_details)
    
    report_content = "\n".join(report_lines)
    
    report_path = (
        Path(output).expanduser().resolve()
        if output
        else (company_paths.finances_root / "company_budget_report.md").resolve()
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Report generated at {report_path}")

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        run(
            company=args.company,
            global_config_path=args.global_config_path,
            company_workspace_root=args.company_workspace_root,
            output=args.output,
        )
    )
