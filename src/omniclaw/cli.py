from __future__ import annotations

import argparse
import logging
from typing import Sequence

import uvicorn

from omniclaw.app import create_app
from omniclaw.config import build_settings
from omniclaw.litellm_runtime import ensure_local_litellm_proxy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the OmniClaw kernel.")
    parser.add_argument(
        "--company",
        help="Registered company slug or display name from ~/.omniClaw/config.json.",
    )
    parser.add_argument(
        "--global-config-path",
        help="Override the OmniClaw global config path (default: ~/.omniClaw/config.json).",
    )
    parser.add_argument(
        "--company-workspace-root",
        help="Legacy explicit company workspace root override.",
    )
    parser.add_argument(
        "--company-config-path",
        help="Legacy explicit company config path override.",
    )
    parser.add_argument(
        "--database-url",
        help="Explicit SQLAlchemy database URL (default: sqlite under the selected company workspace).",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    settings = build_settings(
        company=args.company,
        global_config_path=args.global_config_path,
        company_workspace_root=args.company_workspace_root,
        company_config_path=args.company_config_path,
        database_url=args.database_url,
    )
    app = create_app(settings)
    logger = logging.getLogger(__name__)
    with ensure_local_litellm_proxy(settings, logger=logger):
        uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
