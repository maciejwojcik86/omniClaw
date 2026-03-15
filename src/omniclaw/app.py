import asyncio
from contextlib import asynccontextmanager, suppress
import logging

from fastapi import FastAPI
from fastapi import HTTPException

from omniclaw.config import Settings, load_settings
from omniclaw.db.repository import KernelRepository
from omniclaw.db.session import create_engine_from_url, create_session_factory, require_database_at_head
from omniclaw.forms import FormsActionRequest, FormsService, FormsWorkspaceSyncRequest
from omniclaw.instructions import InstructionsActionRequest, InstructionsService
from omniclaw.ipc import IpcActionRequest, IpcRouterService
from omniclaw.logging import configure_logging
from omniclaw.provisioning import (
    MockProvisioningAdapter,
    ProvisioningActionRequest,
    ProvisioningService,
    SystemProvisioningAdapter,
)
from omniclaw.runtime import RuntimeActionRequest, RuntimeService
from omniclaw.budgets.schemas import BudgetActionRequest
from omniclaw.budgets.service import BudgetService
from omniclaw.usage.routes import build_usage_router
from omniclaw.usage.service import UsageService


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    configure_logging(resolved_settings.log_level)
    logger = logging.getLogger(__name__)

    engine = create_engine_from_url(resolved_settings.database_url)
    require_database_at_head(resolved_settings.database_url, engine=engine)
    session_factory = create_session_factory(resolved_settings.database_url, engine=engine)
    repository = KernelRepository(session_factory)
    mock_adapter = MockProvisioningAdapter()
    system_adapter = SystemProvisioningAdapter(
        helper_path=resolved_settings.provisioning_helper_path,
        helper_use_sudo=resolved_settings.provisioning_helper_use_sudo,
    )
    instructions_service = InstructionsService(settings=resolved_settings, repository=repository)
    ipc_service = IpcRouterService(
        settings=resolved_settings,
        repository=repository,
        instructions_service=instructions_service,
    )

    async def _ipc_scan_loop(stop_event: asyncio.Event) -> None:
        interval = max(1, resolved_settings.ipc_router_scan_interval_seconds)
        while not stop_event.is_set():
            try:
                result = await asyncio.to_thread(ipc_service.execute, IpcActionRequest(action="scan_forms"))
                summary = result.get("summary", {})
                scanned = int(summary.get("scanned", 0))
                routed = int(summary.get("routed", 0))
                undelivered = int(summary.get("undelivered", 0))
                if scanned or routed or undelivered:
                    logger.info(
                        "ipc auto-scan tick: scanned=%s routed=%s undelivered=%s",
                        scanned,
                        routed,
                        undelivered,
                    )
            except Exception:
                logger.exception("ipc auto-scan tick failed")

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue

    async def _budget_maintenance_loop(stop_event: asyncio.Event) -> None:
        interval = max(1, resolved_settings.budget_auto_cycle_poll_interval_seconds)
        service = BudgetService(repository=repository)
        while not stop_event.is_set():
            try:
                result = await service.run_due_cycle()
                if result is not None and result.get("status") == "ok":
                    cycle = result.get("cycle", {})
                    logger.info(
                        "budget cycle tick: cycle_date=%s synced_caps=%s",
                        cycle.get("cycle_date"),
                        result.get("synced_caps", 0),
                    )
            except Exception:
                logger.exception("budget maintenance tick failed")

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        stop_event: asyncio.Event | None = None
        scan_task: asyncio.Task[None] | None = None
        budget_task: asyncio.Task[None] | None = None
        auto_scan_enabled = (
            resolved_settings.ipc_router_auto_scan_enabled and resolved_settings.environment.lower() != "test"
        )
        budget_auto_cycle_enabled = (
            resolved_settings.budget_auto_cycle_enabled and resolved_settings.environment.lower() != "test"
        )
        if auto_scan_enabled:
            stop_event = asyncio.Event()
            scan_task = asyncio.create_task(_ipc_scan_loop(stop_event))
            logger.info(
                "ipc auto-scan enabled (interval=%ss)",
                max(1, resolved_settings.ipc_router_scan_interval_seconds),
            )
        if budget_auto_cycle_enabled:
            if stop_event is None:
                stop_event = asyncio.Event()
            budget_task = asyncio.create_task(_budget_maintenance_loop(stop_event))
            logger.info(
                "budget auto-cycle enabled (interval=%ss)",
                max(1, resolved_settings.budget_auto_cycle_poll_interval_seconds),
            )
        try:
            yield
        finally:
            if stop_event is not None:
                stop_event.set()
            if scan_task is not None:
                scan_task.cancel()
                with suppress(asyncio.CancelledError):
                    await scan_task
            if budget_task is not None:
                budget_task.cancel()
                with suppress(asyncio.CancelledError):
                    await budget_task

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)

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

    @app.post("/v1/runtime/actions")
    def runtime_actions(request: RuntimeActionRequest) -> dict[str, object]:
        mode = resolved_settings.runtime_mode
        if mode == "mock":
            pass
        elif mode == "system":
            if not resolved_settings.allow_privileged_runtime:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "System runtime control is disabled. "
                        "Set OMNICLAW_ALLOW_PRIVILEGED_RUNTIME=true to enable."
                    ),
                )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Unsupported runtime mode '{mode}'",
            )

        service = RuntimeService(settings=resolved_settings, repository=repository, mode=mode)
        response = service.execute(request)
        response["mode"] = mode
        return response

    @app.post("/v1/ipc/actions")
    def ipc_actions(request: IpcActionRequest) -> dict[str, object]:
        return ipc_service.execute(request)

    @app.post("/v1/instructions/actions")
    def instructions_actions(request: InstructionsActionRequest) -> dict[str, object]:
        return instructions_service.execute(request)

    @app.post("/v1/forms/actions")
    def forms_actions(request: FormsActionRequest) -> dict[str, object]:
        service = FormsService(repository=repository)
        return service.execute(request)

    @app.post("/v1/forms/workspace/sync")
    def forms_workspace_sync(request: FormsWorkspaceSyncRequest | None = None) -> dict[str, object]:
        service = FormsService(repository=repository)
        payload = request or FormsWorkspaceSyncRequest()
        return service.sync_workspace_form_types(
            prune_missing=payload.prune_missing,
            activate=payload.activate,
        )

    @app.post("/v1/budgets/actions")
    async def budgets_actions(request: BudgetActionRequest) -> dict[str, object]:
        service = BudgetService(repository=repository)
        return await service.execute(request)

    app.include_router(build_usage_router(lambda: UsageService(repository=repository)))

    return app
