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
class AgentRow:
    node_id: str
    name: str
    linux_uid: int | None
    status: str
    autonomy_level: int


@dataclass
class FsInfo:
    path: str
    owner: str
    group: str
    mode: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List agents and workspace permissions using SQLite node data.")
    parser.add_argument(
        "--database",
        default="omniclaw.db",
        help="Path to SQLite database file (default: omniclaw.db)",
    )
    return parser.parse_args()


def load_agents(db_path: Path) -> list[AgentRow]:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, linux_uid, status, autonomy_level
            FROM nodes
            WHERE type = 'AGENT'
            ORDER BY created_at ASC
            """
        )
        rows = [AgentRow(*row) for row in cur.fetchall()]
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
    db_path = Path(args.database).expanduser().resolve()

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    agents = load_agents(db_path)
    if not agents:
        print(f"No AGENT rows found in {db_path}")
        return 0

    table_rows: list[list[str]] = [
        [
            "node_name",
            "status",
            "autonomy",
            "uid",
            "linux_user",
            "home_owner:group/mode",
            "nullclaw_owner:group/mode",
            "config_owner:group/mode",
            "workspace_owner:group/mode",
        ]
    ]

    for agent in agents:
        username = resolve_username(agent.linux_uid)
        home_path = Path("<unknown>")
        nullclaw_path = Path("<unknown>")
        config_path = Path("<unknown>")
        workspace_path = Path("<unknown>")
        if username and not username.startswith("<"):
            try:
                home_path = Path(pwd.getpwnam(username).pw_dir)
                nullclaw_path = home_path / ".nullclaw"
                config_path = nullclaw_path / "config.json"
                workspace_path = nullclaw_path / "workspace"
            except KeyError:
                pass

        home_info = stat_info(home_path) if str(home_path) != "<unknown>" else FsInfo("<unknown>", "<unknown>", "<unknown>", "<unknown>")
        nullclaw_info = (
            stat_info(nullclaw_path)
            if str(nullclaw_path) != "<unknown>"
            else FsInfo("<unknown>", "<unknown>", "<unknown>", "<unknown>")
        )
        config_info = (
            stat_info(config_path)
            if str(config_path) != "<unknown>"
            else FsInfo("<unknown>", "<unknown>", "<unknown>", "<unknown>")
        )
        workspace_info = (
            stat_info(workspace_path)
            if str(workspace_path) != "<unknown>"
            else FsInfo("<unknown>", "<unknown>", "<unknown>", "<unknown>")
        )

        table_rows.append(
            [
                agent.name,
                agent.status,
                str(agent.autonomy_level),
                str(agent.linux_uid) if agent.linux_uid is not None else "<null>",
                username,
                f"{home_info.owner}:{home_info.group}/{home_info.mode}",
                f"{nullclaw_info.owner}:{nullclaw_info.group}/{nullclaw_info.mode}",
                f"{config_info.owner}:{config_info.group}/{config_info.mode}",
                f"{workspace_info.owner}:{workspace_info.group}/{workspace_info.mode}",
            ]
        )

    print_table(table_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
