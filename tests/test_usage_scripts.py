from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_usage_retry_state_script_dry_run() -> None:
    result = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts" / "usage" / "get_retry_state.sh"),
            "--node-id",
            "demo-node",
            "--retry-status",
            "pending",
            "--limit",
            "5",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "/v1/usage/retries?node_id=demo-node&retry_status=pending&limit=5" in result.stdout


def test_usage_failure_trends_script_dry_run() -> None:
    result = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts" / "usage" / "get_failure_trends.sh"),
            "--provider",
            "openrouter",
            "--model",
            "openrouter/test-model",
            "--limit",
            "10",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "/v1/usage/failure-trends?provider=openrouter&model=openrouter%2Ftest-model&limit=10" in result.stdout
