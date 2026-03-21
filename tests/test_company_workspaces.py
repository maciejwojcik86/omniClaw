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


def test_migrate_repo_workspace_script_is_retired(tmp_path: Path) -> None:
    global_config_path = tmp_path / ".omniClaw" / "config.json"
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
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "has been retired" in result.stdout
    assert "docs/company-workspace-requirements.md" in result.stdout
