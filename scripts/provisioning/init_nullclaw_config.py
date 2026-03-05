#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import pwd
import subprocess

BASE_CONFIG = {
    "default_temperature": 0.7,
    "models": {
        "providers": {},
    },
    "agents": {
        "defaults": {
            "model": {
                "primary": "",
            },
            "heartbeat": {
                "every": "30m",
            },
        }
    },
    "channels": {
        "cli": True,
    },
    "autonomy": {
        "level": "supervised",
        "workspace_only": True,
        "max_actions_per_hour": 20,
    },
    "gateway": {
        "port": 3000,
        "host": "127.0.0.1",
        "require_pairing": True,
    },
    "security": {
        "sandbox": {
            "backend": "auto",
        },
        "audit": {
            "enabled": True,
        },
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize ~/.nullclaw/config.json with a provider-empty baseline.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--config-path", default="")
    parser.add_argument("--force", action="store_true", help="Overwrite existing config file")
    parser.add_argument("--apply", action="store_true", help="Apply filesystem changes (default: dry-run)")
    return parser.parse_args()


def resolve_user_home(username: str, *, allow_missing: bool = False) -> Path:
    try:
        return Path(pwd.getpwnam(username).pw_dir)
    except KeyError as exc:
        if allow_missing:
            return Path("/home") / username
        raise SystemExit(f"User not found: {username}") from exc


def resolve_user_ids(username: str) -> tuple[int, int]:
    try:
        entry = pwd.getpwnam(username)
    except KeyError as exc:
        raise SystemExit(f"User not found: {username}") from exc
    return entry.pw_uid, entry.pw_gid


def _parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def helper_command(*args: str) -> list[str]:
    helper_path = os.getenv("OMNICLAW_PROVISIONING_HELPER_PATH", "").strip()
    helper_use_sudo = _parse_bool(os.getenv("OMNICLAW_PROVISIONING_HELPER_USE_SUDO"))
    if not helper_path:
        raise SystemExit(
            "Apply mode as non-root requires OMNICLAW_PROVISIONING_HELPER_PATH "
            "or direct root execution."
        )
    if not os.access(helper_path, os.X_OK):
        raise SystemExit(f"Configured provisioning helper is not executable: {helper_path}")
    prefix = ["sudo", "-n"] if helper_use_sudo else []
    return [*prefix, helper_path, *args]


def main() -> int:
    args = parse_args()
    home = resolve_user_home(args.username, allow_missing=not args.apply)
    config_path = Path(args.config_path).expanduser().resolve() if args.config_path else (home / ".nullclaw" / "config.json")
    owner_uid = None
    owner_gid = None

    if not args.apply:
        print("DRY-RUN mode. Use --apply to write config.")
        if not config_path.exists():
            print(f"DRY-RUN note: user '{args.username}' may not exist yet; using inferred path '{home}'.")
    else:
        if os.geteuid() != 0:
            if args.config_path:
                raise SystemExit(
                    "Apply mode with non-root helper only supports default per-user config path. "
                    "Run as root for custom --config-path."
                )
            cmd = helper_command("init_user_nullclaw_config", args.username, "force" if args.force else "")
            cmd = [part for part in cmd if part != ""]
            subprocess.run(cmd, check=True)
            try:
                exists = config_path.exists()
            except PermissionError:
                print(f"WRITE file {config_path} (provisioned via helper; access denied to verify)")
                return 0
            if exists:
                print(f"EXISTS file {config_path} (provisioned via helper)")
            else:
                print(f"WRITE file {config_path} (provisioned via helper)")
            return 0
        owner_uid, owner_gid = resolve_user_ids(args.username)

    if config_path.exists() and not args.force:
        print(f"EXISTS file {config_path} (use --force to overwrite)")
        return 0

    print(f"WRITE file {config_path}")
    if args.apply:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(BASE_CONFIG, indent=2) + "\n", encoding="utf-8")
        assert owner_uid is not None and owner_gid is not None
        os.chown(config_path.parent, owner_uid, owner_gid)
        os.chown(config_path, owner_uid, owner_gid)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
