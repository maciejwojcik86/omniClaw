#!/usr/bin/env python3
from __future__ import annotations

import sys


MESSAGE = """bootstrap_company_workspace.py has been retired.

OmniClaw now expects one explicitly configured workspace per company from ~/.omniClaw/config.json,
with no repo-workspace bootstrap fallback.

Create and populate the company workspace directly, then point the company entry at it.
See: docs/company-workspace-requirements.md
"""


def main() -> int:
    print(MESSAGE.strip())
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
