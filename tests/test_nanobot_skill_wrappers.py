from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SKILL_DIR = REPO_ROOT / "workspace" / "forms" / "deploy_new_agent" / "skills" / "deploy-new-nanobot"
TEMPLATE_ROOT = REPO_ROOT / "workspace" / "nanobot_workspace_templates"


def _seed_repo_root(repo_root: Path) -> None:
    (repo_root / "workspace").mkdir(parents=True, exist_ok=True)
    (repo_root / "pyproject.toml").write_text(
        "[project]\nname = 'nanobot-skill-test'\nversion = '0.0.0'\n",
        encoding="utf-8",
    )
    shutil.copytree(TEMPLATE_ROOT, repo_root / "workspace" / "nanobot_workspace_templates", dirs_exist_ok=True)


def _copy_skill_dir(*, repo_root: Path, source_relative: str, target_relative: str) -> Path:
    source_dir = REPO_ROOT / source_relative
    target_dir = repo_root / target_relative
    shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
    return target_dir


@pytest.mark.parametrize(
    ("source_relative", "target_relative", "script_name", "args", "expected_text"),
    [
        (
            "workspace/forms/deploy_new_agent/skills/deploy-new-nanobot",
            "workspace/forms/deploy_new_agent/skills/deploy-new-nanobot",
            "deploy_new_nanobot.sh",
            ["--node-name", "Test_Agent_01", "--manager-node-name", "Director_01"],
            "DRY-RUN provisioning payload:",
        ),
        (
            "workspace/macos/skills/deploy-new-nanobot",
            "workspace/macos/skills/deploy-new-nanobot",
            "deploy_new_nanobot_agent.sh",
            ["--node-name", "Test_Agent_01", "--manager-node-name", "Director_01"],
            "DRY-RUN provisioning payload:",
        ),
        (
            "workspace/agents/Ops_Head_01/workspace/skills/deploy-new-nanobot",
            "workspace/agents/Ops_Head_01/workspace/skills/deploy-new-nanobot",
            "provision_agent_workflow.sh",
            ["--username", "agent_test", "--manager-node-name", "Director_01"],
            '"node_name": "agent_test"',
        ),
    ],
)
def test_nanobot_skill_entrypoints_run_from_real_distributed_locations(
    tmp_path: Path,
    source_relative: str,
    target_relative: str,
    script_name: str,
    args: list[str],
    expected_text: str,
) -> None:
    repo_root = tmp_path / "repo"
    _seed_repo_root(repo_root)
    target_dir = _copy_skill_dir(
        repo_root=repo_root,
        source_relative=source_relative,
        target_relative=target_relative,
    )

    result = subprocess.run(
        ["bash", str(target_dir / "scripts" / script_name), *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    assert expected_text in result.stdout


def test_create_workspace_tree_uses_nanobot_workspace_templates(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_repo_root(repo_root)
    target_dir = _copy_skill_dir(
        repo_root=repo_root,
        source_relative="workspace/forms/deploy_new_agent/skills/deploy-new-nanobot",
        target_relative="workspace/forms/deploy_new_agent/skills/deploy-new-nanobot",
    )
    workspace_root = repo_root / "workspace" / "agents" / "Template_Test_01" / "workspace"

    subprocess.run(
        [
            "python3",
            str(target_dir / "scripts" / "create_workspace_tree.py"),
            "--apply",
            "--workspace-root",
            str(workspace_root),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    assert (workspace_root / "HEARTBEAT.md").read_text(encoding="utf-8") == (
        repo_root / "workspace" / "nanobot_workspace_templates" / "HEARTBEAT.md"
    ).read_text(encoding="utf-8")
    assert (workspace_root / "AGENTS.md").read_text(encoding="utf-8") == (
        repo_root / "workspace" / "nanobot_workspace_templates" / "AGENTS.placeholder.md"
    ).read_text(encoding="utf-8")


def test_init_nanobot_config_uses_nanobot_workspace_template(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_repo_root(repo_root)
    target_dir = _copy_skill_dir(
        repo_root=repo_root,
        source_relative="workspace/forms/deploy_new_agent/skills/deploy-new-nanobot",
        target_relative="workspace/forms/deploy_new_agent/skills/deploy-new-nanobot",
    )
    workspace_root = repo_root / "workspace" / "agents" / "Template_Test_01" / "workspace"
    config_path = repo_root / "workspace" / "agents" / "Template_Test_01" / "config.json"
    workspace_root.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "python3",
            str(target_dir / "scripts" / "init_nanobot_config.py"),
            "--apply",
            "--workspace-root",
            str(workspace_root),
            "--config-path",
            str(config_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["tools"]["restrictToWorkspace"] is False
    assert payload["agents"]["defaults"]["workspace"] == str(workspace_root.resolve())


def test_write_agent_instructions_uses_nanobot_workspace_template(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_repo_root(repo_root)
    target_dir = _copy_skill_dir(
        repo_root=repo_root,
        source_relative="workspace/forms/deploy_new_agent/skills/deploy-new-nanobot",
        target_relative="workspace/forms/deploy_new_agent/skills/deploy-new-nanobot",
    )
    workspace_root = repo_root / "workspace" / "agents" / "Template_Test_01" / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "python3",
            str(target_dir / "scripts" / "write_agent_instructions.py"),
            "--apply",
            "--workspace-root",
            str(workspace_root),
            "--node-name",
            "Template_Test_01",
            "--role-name",
            "Template Role",
            "--manager-name",
            "Director_01",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    text = (workspace_root / "AGENTS.md").read_text(encoding="utf-8")
    assert "Template Role" in text
    assert "Template_Test_01" in text
    assert "Director_01" in text
    template_text = (
        repo_root / "workspace" / "nanobots_instructions" / "Template_Test_01" / "AGENTS.md"
    ).read_text(encoding="utf-8")
    assert "{{node.role_name}}" in template_text
