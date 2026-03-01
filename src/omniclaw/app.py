from fastapi import FastAPI
from fastapi import HTTPException

from omniclaw.config import Settings, load_settings
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_engine_from_url, create_session_factory, init_db
from omniclaw.logging import configure_logging
from omniclaw.provisioning import (
    MockProvisioningAdapter,
    ProvisioningActionRequest,
    ProvisioningService,
    SystemProvisioningAdapter,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    configure_logging(resolved_settings.log_level)

    app = FastAPI(title=resolved_settings.app_name)
    engine = create_engine_from_url(resolved_settings.database_url)
    init_db(engine)
    session_factory = create_session_factory(resolved_settings.database_url, engine=engine)
    repository = KernelRepository(session_factory)
    mock_adapter = MockProvisioningAdapter()
    system_adapter = SystemProvisioningAdapter()

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "service": resolved_settings.app_name,
            "environment": resolved_settings.environment,
        }

    @app.post("/v1/provisioning/actions")
    def provisioning_actions(request: ProvisioningActionRequest) -> dict[str, object]:
        mode = resolved_settings.provisioning_mode
        if mode == "mock":
            adapter = mock_adapter
        elif mode == "system":
            if not resolved_settings.allow_privileged_provisioning:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "System provisioning is disabled. "
                        "Set OMNICLAW_ALLOW_PRIVILEGED_PROVISIONING=true to enable."
                    ),
                )
            adapter = system_adapter
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Unsupported provisioning mode '{mode}'",
            )

        service = ProvisioningService(adapter=adapter, repository=repository)
        response = service.execute(request)
        response["mode"] = mode
        return response

    return app
