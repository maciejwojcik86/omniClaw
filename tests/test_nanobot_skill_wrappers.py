from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures"
CANONICAL_SKILL_DIR = FIXTURES_ROOT / "deploy-new-nanobot-skill"
TEMPLATE_ROOT = FIXTURES_ROOT / "nanobot_workspace_templates"


def _seed_repo_root(repo_root: Path) -> None:
    (repo_root / "workspace").mkdir(parents=True, exist_ok=True)
    (repo_root / "pyproject.toml").write_text(
        "[project]\nname = 'nanobot-skill-test'\nversion = '0.0.0'\n",
        encoding="utf-8",
    )
    shutil.copytree(TEMPLATE_ROOT, repo_root / "workspace" / "nanobot_workspace_templates", dirs_exist_ok=True)


def _write_global_config(repo_root: Path) -> Path:
    global_config_path = repo_root / ".omniClaw" / "config.json"
    global_config_path.parent.mkdir(parents=True, exist_ok=True)
    global_config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "companies": {
                    "skill-test": {
                        "display_name": "Skill Test",
                        "workspace_root": str((repo_root / "workspace").resolve()),
                        "instructions": {"access_scope": "descendant"},
                        "budgeting": {
                            "daily_company_budget_usd": 0,
                            "root_allocator_node": "UNSET_ROOT_ALLOCATOR",
                            "reset_time_utc": "00:00",
                        },
                        "hierarchy": {"top_agent_node": "UNSET_TOP_AGENT"},
                        "skills": {"default_agent_skill_names": ["form_workflow_authoring"]},
                        "models": [],
                        "runtime": {
                            "ipc_router_auto_scan_enabled": True,
                            "ipc_router_scan_interval_seconds": 5,
                            "budget_auto_cycle_enabled": True,
                            "budget_auto_cycle_poll_interval_seconds": 60,
                        },
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return global_config_path


def _copy_skill_dir(*, repo_root: Path, source_relative: str, target_relative: str) -> Path:
    source_dir = REPO_ROOT / source_relative
    target_dir = repo_root / target_relative
    shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
    return target_dir


@pytest.mark.parametrize(
    ("source_relative", "target_relative", "script_name", "args", "expected_text"),
    [
        (
            "tests/fixtures/deploy-new-nanobot-skill",
            "workspace/forms/deploy_new_agent/skills/deploy-new-nanobot",
            "deploy_new_nanobot.sh",
            ["--node-name", "Test_Agent_01", "--manager-node-name", "Director_01"],
            "DRY-RUN provisioning payload:",
        ),
        (
            "tests/fixtures/deploy-new-nanobot-skill",
            "workspace/macos/skills/deploy-new-nanobot",
            "deploy_new_nanobot_agent.sh",
            ["--node-name", "Test_Agent_01", "--manager-node-name", "Director_01"],
            "DRY-RUN provisioning payload:",
        ),
        (
            "tests/fixtures/deploy-new-nanobot-standalone",
            "workspace/master_skills/deploy-new-nanobot-standalone",
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
    global_config_path = _write_global_config(repo_root)
    env = {
        **os.environ,
        "OMNICLAW_COMPANY": "skill-test",
        "OMNICLAW_GLOBAL_CONFIG_PATH": str(global_config_path),
    }
    target_dir = _copy_skill_dir(
        repo_root=repo_root,
        source_relative=source_relative,
        target_relative=target_relative,
    )

    result = subprocess.run(
        ["bash", str(target_dir / "scripts" / script_name), *args],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert expected_text in result.stdout


def test_create_workspace_tree_uses_nanobot_workspace_templates(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_repo_root(repo_root)
    global_config_path = _write_global_config(repo_root)
    env = {
        **os.environ,
        "OMNICLAW_COMPANY": "skill-test",
        "OMNICLAW_GLOBAL_CONFIG_PATH": str(global_config_path),
    }
    target_dir = _copy_skill_dir(
        repo_root=repo_root,
        source_relative="tests/fixtures/deploy-new-nanobot-skill",
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
        env=env,
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
    global_config_path = _write_global_config(repo_root)
    env = {
        **os.environ,
        "OMNICLAW_COMPANY": "skill-test",
        "OMNICLAW_GLOBAL_CONFIG_PATH": str(global_config_path),
    }
    target_dir = _copy_skill_dir(
        repo_root=repo_root,
        source_relative="tests/fixtures/deploy-new-nanobot-skill",
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
        env=env,
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
    global_config_path = _write_global_config(repo_root)
    env = {
        **os.environ,
        "OMNICLAW_COMPANY": "skill-test",
        "OMNICLAW_GLOBAL_CONFIG_PATH": str(global_config_path),
    }
    target_dir = _copy_skill_dir(
        repo_root=repo_root,
        source_relative="tests/fixtures/deploy-new-nanobot-skill",
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
        env=env,
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
