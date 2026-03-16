from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.config import build_settings
from omniclaw.company_paths import build_company_paths
from omniclaw.db.enums import MasterSkillLifecycleStatus, NodeStatus, NodeType, SkillValidationStatus
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_session_factory
from tests.helpers import migrate_database_to_head, write_global_company_config


def test_build_settings_defaults_to_home_workspace(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    global_config_path = tmp_path / ".omniClaw" / "config.json"
    expected_root = (tmp_path / ".omniClaw" / "workspace").resolve()
    write_global_company_config(
        path=global_config_path,
        workspace_root=expected_root,
        slug="omniclaw",
        display_name="OmniClaw",
    )
    expected_root.mkdir(parents=True, exist_ok=True)

    settings = build_settings()

    assert settings.company_workspace_root == str(expected_root)
    assert settings.company_slug == "omniclaw"
    assert settings.company_config_path is None
    assert settings.database_url == f"sqlite:///{(expected_root / 'omniclaw.db').resolve()}"


def test_build_settings_uses_explicit_company_workspace_override(tmp_path: Path) -> None:
    company_root = tmp_path / "companies" / "acme"

    settings = build_settings(company_workspace_root=company_root)

    assert settings.company_workspace_root == str(company_root.resolve())
    assert settings.company_config_path == str((company_root / "config.json").resolve())
    assert settings.database_url == f"sqlite:///{(company_root / 'omniclaw.db').resolve()}"


def test_company_path_resolution_isolated_between_two_roots(tmp_path: Path) -> None:
    alpha_settings = build_settings(company_workspace_root=tmp_path / "companies" / "alpha")
    beta_settings = build_settings(company_workspace_root=tmp_path / "companies" / "beta")

    alpha_paths = build_company_paths(alpha_settings)
    beta_paths = build_company_paths(beta_settings)

    assert alpha_paths.root != beta_paths.root
    assert alpha_paths.database_file != beta_paths.database_file
    assert alpha_paths.agents_root != beta_paths.agents_root
    assert alpha_paths.master_skills_root != beta_paths.master_skills_root
    assert alpha_paths.form_archive_root != beta_paths.form_archive_root


def test_migrate_repo_workspace_copies_and_rewrites_paths(tmp_path: Path) -> None:
    source_root = tmp_path / "repo-workspace"
    target_root = tmp_path / "company-a"
    global_config_path = tmp_path / ".omniClaw" / "config.json"
    source_root.mkdir(parents=True, exist_ok=True)
    (source_root / "agents" / "Worker_01" / "workspace").mkdir(parents=True, exist_ok=True)
    (source_root / "master_skills" / "hello-skill").mkdir(parents=True, exist_ok=True)
    (source_root / "nanobots_instructions" / "Worker_01").mkdir(parents=True, exist_ok=True)
    (source_root / "nanobot_workspace_templates").mkdir(parents=True, exist_ok=True)
    (source_root / "forms" / "message").mkdir(parents=True, exist_ok=True)
    (source_root / "master_skills" / "hello-skill" / "SKILL.md").write_text(
        f"Refer to {source_root}/agents/Worker_01/workspace\n",
        encoding="utf-8",
    )
    (source_root / "company_config.json").write_text(
        json.dumps(
            {
                "instructions": {"access_scope": "descendant"},
                "skills": {"default_agent_skill_names": ["form_workflow_authoring"]},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (source_root / "company_models.yaml").write_text("models: []\n", encoding="utf-8")
    (source_root / "README.md").write_text("Source workspace\n", encoding="utf-8")
    shutil.copytree(ROOT / "workspace" / "nanobot_workspace_templates", source_root / "nanobot_workspace_templates", dirs_exist_ok=True)
    shutil.copytree(ROOT / "workspace" / "forms" / "message", source_root / "forms" / "message", dirs_exist_ok=True)

    database_url = f"sqlite:///{source_root / 'omniclaw.db'}"
    migrate_database_to_head(database_url)
    repository = KernelRepository(create_session_factory(database_url))
    repository.create_node(
        node_type=NodeType.AGENT,
        name="Worker_01",
        status=NodeStatus.ACTIVE,
        workspace_root=str((source_root / "agents" / "Worker_01" / "workspace").resolve()),
        runtime_config_path=str((source_root / "agents" / "Worker_01" / "config.json").resolve()),
        instruction_template_root=str((source_root / "nanobots_instructions" / "Worker_01").resolve()),
    )
    repository.upsert_master_skill(
        name="hello-skill",
        description="Hello",
        version="1.0.0",
        validation_status=SkillValidationStatus.VALIDATED,
        lifecycle_status=MasterSkillLifecycleStatus.ACTIVE,
        master_path=str((source_root / "master_skills" / "hello-skill").resolve()),
        form_type_key=None,
    )

    env = {**os.environ, "PYTHONPATH": f"{SRC}{os.pathsep}{os.environ.get('PYTHONPATH', '')}".rstrip(os.pathsep)}
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(ROOT / "scripts" / "company" / "migrate_repo_workspace.py"),
            "--apply",
            "--company",
            "acme",
            "--global-config-path",
            str(global_config_path),
            "--source-workspace-root",
            str(source_root),
            "--company-workspace-root",
            str(target_root),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Migration applied." in result.stdout
    assert not (target_root / "config.json").exists()
    assert not (target_root / "company_config.json").exists()
    assert not (target_root / "models" / "company_models.yaml").exists()

    registry_payload = json.loads(global_config_path.read_text(encoding="utf-8"))
    company_entry = registry_payload["companies"]["acme"]
    assert company_entry["display_name"] == "Acme"
    assert company_entry["workspace_root"] == str(target_root.resolve())
    assert company_entry["skills"]["default_agent_skill_names"] == ["form_workflow_authoring"]
    assert company_entry["models"] == []

    target_repository = KernelRepository(create_session_factory(f"sqlite:///{target_root / 'omniclaw.db'}"))
    node = target_repository.get_node(node_name="Worker_01")
    assert node is not None
    assert node.workspace_root == str((target_root / "agents" / "Worker_01" / "workspace").resolve())
    assert node.runtime_config_path == str((target_root / "agents" / "Worker_01" / "config.json").resolve())
    assert node.instruction_template_root == str((target_root / "nanobots_instructions" / "Worker_01").resolve())

    skill = target_repository.get_master_skill(name="hello-skill")
    assert skill is not None
    assert skill.master_path == str((target_root / "master_skills" / "hello-skill").resolve())
    assert str(target_root) in (target_root / "master_skills" / "hello-skill" / "SKILL.md").read_text(encoding="utf-8")
