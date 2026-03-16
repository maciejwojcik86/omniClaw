#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.company_paths import build_company_paths
from omniclaw.config import build_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare agent skill assignments in the DB against deployed workspace skills.",
    )
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
    parser.add_argument(
        "--node-name",
        dest="node_names",
        action="append",
        default=[],
        help="Agent node name to audit. Repeat to audit multiple agents. Defaults to all active agents.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of text.",
    )
    return parser.parse_args()


def load_nodes(conn: sqlite3.Connection, *, node_names: list[str]) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if node_names:
        placeholders = ",".join("?" for _ in node_names)
        cur.execute(
            f"""
            SELECT id, name, workspace_root
            FROM nodes
            WHERE type = 'AGENT' AND name IN ({placeholders})
            ORDER BY name
            """,
            node_names,
        )
    else:
        cur.execute(
            """
            SELECT id, name, workspace_root
            FROM nodes
            WHERE type = 'AGENT' AND status = 'ACTIVE'
            ORDER BY name
            """
        )
    return list(cur.fetchall())


def load_expected_skills(conn: sqlite3.Connection, *, node_id: str) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            ms.name AS skill_name,
            GROUP_CONCAT(DISTINCT nsa.assignment_source) AS assignment_sources
        FROM node_skill_assignments AS nsa
        JOIN master_skills AS ms ON ms.id = nsa.skill_id
        WHERE nsa.node_id = ?
        GROUP BY ms.name
        ORDER BY ms.name
        """,
        (node_id,),
    )
    items: list[dict[str, Any]] = []
    for row in cur.fetchall():
        raw_sources = row["assignment_sources"] or ""
        sources = sorted(source for source in raw_sources.split(",") if source)
        items.append(
            {
                "name": row["skill_name"],
                "assignment_sources": sources,
            }
        )
    return items


def load_workspace_skills(*, workspace_root: str | None) -> list[str]:
    if not workspace_root:
        return []
    skills_root = Path(workspace_root) / "skills"
    if not skills_root.exists() or not skills_root.is_dir():
        return []
    return sorted(
        item.name
        for item in skills_root.iterdir()
        if item.is_dir()
    )


def build_report(conn: sqlite3.Connection, *, node_names: list[str]) -> list[dict[str, Any]]:
    report: list[dict[str, Any]] = []
    for node in load_nodes(conn, node_names=node_names):
        expected = load_expected_skills(conn, node_id=node["id"])
        expected_names = sorted(item["name"] for item in expected)
        actual_names = load_workspace_skills(workspace_root=node["workspace_root"])
        report.append(
            {
                "node_name": node["name"],
                "workspace_root": node["workspace_root"],
                "expected_skills": expected,
                "actual_workspace_skills": actual_names,
                "missing_from_workspace": sorted(set(expected_names) - set(actual_names)),
                "extra_in_workspace": sorted(set(actual_names) - set(expected_names)),
                "matches": set(expected_names) == set(actual_names),
            }
        )
    return report


def render_text(report: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in report:
        lines.append(f"node={item['node_name']}")
        lines.append(f"workspace_root={item['workspace_root']}")
        expected = item["expected_skills"]
        if expected:
            lines.append("expected_skills:")
            for skill in expected:
                sources = ",".join(skill["assignment_sources"])
                lines.append(f"  - {skill['name']} [{sources}]")
        else:
            lines.append("expected_skills: []")
        lines.append(f"actual_workspace_skills: {json.dumps(item['actual_workspace_skills'])}")
        lines.append(f"missing_from_workspace: {json.dumps(item['missing_from_workspace'])}")
        lines.append(f"extra_in_workspace: {json.dumps(item['extra_in_workspace'])}")
        lines.append(f"matches: {str(item['matches']).lower()}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    if args.database:
        database_path = Path(args.database).expanduser().resolve()
    else:
        settings = build_settings(
            company=args.company,
            global_config_path=args.global_config_path,
            company_workspace_root=args.company_workspace_root,
        )
        database_path = build_company_paths(settings).database_file
    if not database_path.exists():
        raise SystemExit(f"database not found: {database_path}")

    conn = sqlite3.connect(database_path)
    try:
        report = build_report(conn, node_names=args.node_names)
    finally:
        conn.close()

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
