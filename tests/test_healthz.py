from pathlib import Path
import sys

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.app import create_app
from omniclaw.config import Settings


def test_healthz_returns_expected_payload() -> None:
    app = create_app(
        Settings(
            app_name="omniclaw-kernel",
            environment="test",
            log_level="INFO",
            database_url="sqlite:///:memory:",
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
