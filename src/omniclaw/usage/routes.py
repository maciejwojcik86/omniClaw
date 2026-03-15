from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Query, status

from omniclaw.usage.schemas import (
    SessionExportRequest,
    SessionExportResponse,
    UsageRecentSessionsResponse,
    UsageSessionSummaryResponse,
)
from omniclaw.usage.service import UsageService


def build_usage_router(service_factory: Callable[[], UsageService]) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["usage"])

    @router.post("/sessions/export", response_model=SessionExportResponse)
    def export_session(request: SessionExportRequest) -> SessionExportResponse:
        usage_svc = service_factory()
        try:
            return usage_svc.export_agent_session(request=request)
        except FileNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.get("/usage/sessions/{session_key}/summary", response_model=UsageSessionSummaryResponse)
    def get_session_summary(session_key: str) -> UsageSessionSummaryResponse:
        usage_svc = service_factory()
        try:
            return usage_svc.get_session_summary(session_key=session_key)
        except ValueError as e:
            detail = str(e)
            status_code = status.HTTP_404_NOT_FOUND if detail.startswith("No usage rows") else status.HTTP_400_BAD_REQUEST
            raise HTTPException(status_code=status_code, detail=detail)

    @router.get("/usage/nodes/{node_id}/recent-sessions", response_model=UsageRecentSessionsResponse)
    def list_recent_sessions(
        node_id: str,
        limit: int = Query(default=10, ge=1, le=100),
    ) -> UsageRecentSessionsResponse:
        usage_svc = service_factory()
        try:
            return usage_svc.list_recent_sessions(node_id=node_id, limit=limit)
        except ValueError as e:
            detail = str(e)
            status_code = status.HTTP_404_NOT_FOUND if detail.startswith("Node ") else status.HTTP_400_BAD_REQUEST
            raise HTTPException(status_code=status_code, detail=detail)

    return router
