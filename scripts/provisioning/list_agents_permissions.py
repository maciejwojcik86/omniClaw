#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import grp
from pathlib import Path
import pwd
import sqlite3
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.company_paths import build_company_paths
from omniclaw.config import build_settings


@dataclass
class NodeRow:
    node_id: str
    node_type: str
    name: str
    linux_uid: int | None
    linux_username: str | None
    linux_password: str | None
    workspace_root: str | None
    primary_model: str | None
    gateway_running: int
    gateway_pid: int | None
    gateway_started_at: str | None
    gateway_stopped_at: str | None
    status: str
    autonomy_level: int
    manager_name: str | None
    subordinate_count: int


@dataclass
class FsInfo:
    path: str
    owner: str
    group: str
    mode: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List nodes and workspace permissions using SQLite node data.")
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
        help="Path to SQLite database file. Defaults to <company-workspace-root>/omniclaw.db.",
    )
    return parser.parse_args()


def load_nodes(db_path: Path) -> list[NodeRow]:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
              n.id,
              n.type,
              n.name,
              n.linux_uid,
              n.linux_username,
              n.linux_password,
              n.workspace_root,
              n.primary_model,
              n.gateway_running,
              n.gateway_pid,
              n.gateway_started_at,
              n.gateway_stopped_at,
              n.status,
              n.autonomy_level,
              p.name AS manager_name,
              COALESCE(sc.subordinate_count, 0) AS subordinate_count
            FROM nodes n
            LEFT JOIN hierarchy h ON h.child_node_id = n.id
            LEFT JOIN nodes p ON p.id = h.parent_node_id
            LEFT JOIN (
              SELECT parent_node_id, COUNT(*) AS subordinate_count
              FROM hierarchy
              GROUP BY parent_node_id
            ) sc ON sc.parent_node_id = n.id
            WHERE n.type IN ('AGENT', 'HUMAN')
            ORDER BY n.created_at ASC
            """
        )
        rows = [NodeRow(*row) for row in cur.fetchall()]
        return rows
    finally:
        conn.close()


def resolve_username(uid: int | None) -> str:
    if uid is None:
        return "<uid-missing>"
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return f"<uid-{uid}-not-found>"


def stat_info(path: Path) -> FsInfo:
    try:
        st = path.stat()
        mode = oct(st.st_mode & 0o777)
        owner = pwd.getpwuid(st.st_uid).pw_name
        group = grp.getgrgid(st.st_gid).gr_name
        return FsInfo(path=str(path), owner=owner, group=group, mode=mode)
    except FileNotFoundError:
        return FsInfo(path=str(path), owner="<missing>", group="<missing>", mode="<missing>")
    except PermissionError:
        return FsInfo(path=str(path), owner="<denied>", group="<denied>", mode="<denied>")


def format_row(columns: Iterable[str], widths: list[int]) -> str:
    items = list(columns)
    return " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(items))


def print_table(rows: list[list[str]]) -> None:
    if not rows:
        print("No rows")
        return

    widths = [max(len(row[idx]) for row in rows) for idx in range(len(rows[0]))]
    print(format_row(rows[0], widths))
    print("-+-".join("-" * width for width in widths))
    for row in rows[1:]:
        print(format_row(row, widths))


def main() -> int:
    args = parse_args()
    if args.database:
        db_path = Path(args.database).expanduser().resolve()
    else:
        settings = build_settings(
            company=args.company,
            global_config_path=args.global_config_path,
            company_workspace_root=args.company_workspace_root,
        )
        db_path = build_company_paths(settings).database_file

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    nodes = load_nodes(db_path)
    if not nodes:
        print(f"No HUMAN/AGENT rows found in {db_path}")
        return 0

    table_rows: list[list[str]] = [
        [
            "node_name",
            "node_type",
            "status",
            "autonomy",
            "db_linux_user",
            "manager",
            "subordinates",
            "db_workspace",
            "model",
            "gateway",
            "gateway_pid",
            "password",
            "workspace_owner:group/mode",
        ]
    ]

    for node in nodes:
        workspace_info = FsInfo("<unknown>", "<unknown>", "<unknown>", "<unknown>")
        if node.workspace_root:
            workspace_info = stat_info(Path(node.workspace_root))

        table_rows.append(
            [
                node.name,
                node.node_type,
                node.status,
                str(node.autonomy_level),
                node.linux_username or resolve_username(node.linux_uid),
                node.manager_name or "<none>",
                str(node.subordinate_count),
                node.workspace_root or "<null>",
                node.primary_model or "<null>",
                "running" if bool(node.gateway_running) else "stopped",
                str(node.gateway_pid) if node.gateway_pid is not None else "<null>",
                "set" if node.linux_password else "<null>",
                f"{workspace_info.owner}:{workspace_info.group}/{workspace_info.mode}",
            ]
        )

    print_table(table_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
