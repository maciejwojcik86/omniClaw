#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.company_paths import build_company_paths
from omniclaw.config import build_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show the aggregated LLM cost for one agent session from OmniClaw's usage ledger."
    )
    parser.add_argument("--agent-name", required=True, help="Agent node name, e.g. Director_01")
    parser.add_argument("--session-key", required=True, help="Session key, e.g. cli:hello-20260308-Director_01")
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
        "--database",
        help="Path to the OmniClaw SQLite database. Defaults to <company-workspace-root>/omniclaw.db.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.database:
        database_path = Path(args.database).expanduser().resolve()
    else:
        settings = build_settings(
            company=args.company,
            global_config_path=args.global_config_path,
            company_workspace_root=args.company_workspace_root,
        )
        database_path = build_company_paths(settings).database_file
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            n.name AS agent_name,
            a.session_key,
            COUNT(*) AS llm_calls,
            COALESCE(SUM(a.prompt_tokens), 0) AS prompt_tokens,
            COALESCE(SUM(a.completion_tokens), 0) AS completion_tokens,
            COALESCE(SUM(a.reasoning_tokens), 0) AS reasoning_tokens,
            COALESCE(SUM(a.total_tokens), 0) AS total_tokens,
            COALESCE(SUM(a.estimated_cost_usd), 0) AS estimated_cost_usd,
            MIN(a.start_time) AS first_call_at,
            MAX(a.end_time) AS last_call_at
        FROM agent_llm_calls a
        JOIN nodes n ON n.id = a.node_id
        WHERE n.name = ? AND a.session_key = ?
        GROUP BY n.name, a.session_key
        """,
        (args.agent_name, args.session_key),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        print(
            f"No usage rows found for agent '{args.agent_name}' and session '{args.session_key}'."
        )
        return 1

    print(f"agent_name: {row['agent_name']}")
    print(f"session_key: {row['session_key']}")
    print(f"llm_calls: {row['llm_calls']}")
    print(f"prompt_tokens: {row['prompt_tokens']}")
    print(f"completion_tokens: {row['completion_tokens']}")
    print(f"reasoning_tokens: {row['reasoning_tokens']}")
    print(f"total_tokens: {row['total_tokens']}")
    print(f"estimated_cost_usd: {float(row['estimated_cost_usd']):.7f}")
    print(f"first_call_at: {row['first_call_at']}")
    print(f"last_call_at: {row['last_call_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
