#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show the aggregated LLM cost for one agent session from OmniClaw's usage ledger."
    )
    parser.add_argument("--agent-name", required=True, help="Agent node name, e.g. Director_01")
    parser.add_argument("--session-key", required=True, help="Session key, e.g. cli:hello-20260308-Director_01")
    parser.add_argument(
        "--database",
        default="/home/macos/omniClaw/workspace/omniclaw.db",
        help="Path to the OmniClaw SQLite database",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    database_path = Path(args.database).expanduser().resolve()
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
