#!/usr/bin/env python3
from __future__ import annotations

import sys


MESSAGE = """migrate_repo_workspace.py has been retired.

OmniClaw now expects one explicitly configured workspace per company from ~/.omniClaw/config.json,
with no repo-workspace migration path and no repo-workspace runtime fallback.

Populate the company workspace directly and keep that path as the only source of truth.
See: docs/company-workspace-requirements.md
"""


def main() -> int:
    print(MESSAGE.strip())
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
