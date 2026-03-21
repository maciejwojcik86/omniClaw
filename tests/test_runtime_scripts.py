from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_retry_control_script_dry_run() -> None:
    result = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts" / "runtime" / "retry_control.sh"),
            "--action",
            "retry_now",
            "--task-key",
            "invoke_prompt:test-node:cli:test",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert '"action": "retry_now"' in result.stdout
    assert '"task_key": "invoke_prompt:test-node:cli:test"' in result.stdout
