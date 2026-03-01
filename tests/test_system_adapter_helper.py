from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.provisioning.system_adapter import SystemProvisioningAdapter


class _CompletedProcess:
    def __init__(self, returncode: int = 0, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout


def test_helper_mode_routes_commands_without_direct_useradd(monkeypatch) -> None:
    adapter = SystemProvisioningAdapter(
        helper_path="/opt/omniclaw/privileged_provisioning_helper.sh",
        helper_use_sudo=True,
    )
    calls: list[list[str]] = []
    state = {"lookup_count": 0}

    def fake_run(command, capture_output, text, check):
        del capture_output, text
        calls.append(list(command))

        if command[-2:] == ["id_uid", "agent_director_01"]:
            state["lookup_count"] += 1
            if state["lookup_count"] == 1:
                return _CompletedProcess(returncode=1)
            return _CompletedProcess(returncode=0, stdout="21000\n")

        if check:
            return _CompletedProcess(returncode=0)
        return _CompletedProcess(returncode=0)

    monkeypatch.setattr("subprocess.run", fake_run)

    result = adapter.ensure_user(
        username="agent_director_01",
        home_dir="/home/agent_director_01",
        shell="/bin/bash",
        groups=["sudo"],
    )

    assert result.created is True
    assert result.uid == 21000

    expected_prefix = ["sudo", "-n", "/opt/omniclaw/privileged_provisioning_helper.sh"]
    assert calls[0] == expected_prefix + ["id_uid", "agent_director_01"]
    assert calls[1] == expected_prefix + [
        "create_user",
        "agent_director_01",
        "/home/agent_director_01",
        "/bin/bash",
        "",
    ]
    assert calls[2] == expected_prefix + ["id_uid", "agent_director_01"]
    assert calls[3] == expected_prefix + ["add_groups", "agent_director_01", "sudo"]


def test_helper_mode_workspace_preview_remains_idempotent(monkeypatch, tmp_path: Path) -> None:
    adapter = SystemProvisioningAdapter(
        helper_path="/opt/omniclaw/privileged_provisioning_helper.sh",
        helper_use_sudo=False,
    )
    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, check):
        del capture_output, text, check
        calls.append(list(command))
        return _CompletedProcess(returncode=0)

    monkeypatch.setattr("subprocess.run", fake_run)

    workspace = tmp_path / "workspace"
    result = adapter.ensure_workspace(workspace_root=workspace)

    assert result.workspace_root == str(workspace.resolve())
    assert str(workspace.resolve()) in result.created_dirs
    assert workspace.exists() is False
    assert calls == [[
        "/opt/omniclaw/privileged_provisioning_helper.sh",
        "create_workspace",
        str(workspace.resolve()),
    ]]
