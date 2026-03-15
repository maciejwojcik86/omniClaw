#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import grp
from pathlib import Path
import pwd
import sqlite3
from typing import Iterable


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


def find_repo_root(start: Path) -> Path | None:
    current = start.resolve()
    while True:
        if (current / "pyproject.toml").exists() and (current / "workspace").exists():
            return current
        if current == current.parent:
            return None
        current = current.parent


def parse_args() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__).resolve().parent)
    default_db = repo_root / "workspace" / "omniclaw.db" if repo_root else Path("workspace/omniclaw.db")
    parser = argparse.ArgumentParser(description="List nodes and workspace permissions using SQLite node data.")
    parser.add_argument("--database", default=str(default_db), help="Path to SQLite database file")
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
        return [NodeRow(*row) for row in cur.fetchall()]
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
    db_path = Path(args.database).expanduser().resolve()

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    nodes = load_nodes(db_path)
    if not nodes:
        print(f"No HUMAN/AGENT rows found in {db_path}")
        return 0

    table_rows: list[list[str]] = [[
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
    ]]

    for node in nodes:
        workspace_info = FsInfo("<unknown>", "<unknown>", "<unknown>", "<unknown>")
        if node.workspace_root:
            workspace_info = stat_info(Path(node.workspace_root))

        table_rows.append([
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
        ])

    print_table(table_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
