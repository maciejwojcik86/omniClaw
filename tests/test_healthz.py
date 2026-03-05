from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.app import create_app
from omniclaw.config import Settings
from tests.helpers import migrate_database_to_head


def test_healthz_returns_expected_payload(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'healthz.db'}"
    migrate_database_to_head(database_url)
    app = create_app(
        Settings(
            app_name="omniclaw-kernel",
            environment="test",
            log_level="INFO",
            database_url=database_url,
            provisioning_mode="mock",
            allow_privileged_provisioning=False,
        )
    )
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "omniclaw-kernel",
        "environment": "test",
    }


def test_app_startup_fails_when_database_not_migrated(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'healthz-unmigrated.db'}"
    with pytest.raises(RuntimeError, match="Run `uv run alembic upgrade head`"):
        create_app(
            Settings(
                app_name="omniclaw-kernel",
                environment="test",
                log_level="INFO",
                database_url=database_url,
                provisioning_mode="mock",
                allow_privileged_provisioning=False,
            )
        )
