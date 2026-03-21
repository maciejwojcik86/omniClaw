from __future__ import annotations

import logging
import shutil
from collections import Counter
from decimal import Decimal
from pathlib import Path

from nanobot.session.manager import SessionManager

from omniclaw.db.repository import KernelRepository
from omniclaw.usage.schemas import (
    ProviderModelFailureTrendItem,
    ProviderModelFailureTrendsResponse,
    RetryStateItem,
    RetryStateResponse,
    SessionExportRequest,
    SessionExportResponse,
    UsageRecentSessionItem,
    UsageRecentSessionsResponse,
    UsageSessionSummaryResponse,
)

logger = logging.getLogger(__name__)


class UsageService:
    def __init__(self, repository: KernelRepository):
        self.repo = repository

    def export_agent_session(self, request: SessionExportRequest, destination_dir: str = "/tmp/omniclaw_exports") -> SessionExportResponse:
        node = self.repo.get_node(node_id=request.node_id)
        if not node:
            raise ValueError(f"Node {request.node_id} not found")

        if not node.workspace_root:
            raise ValueError(f"Node {request.node_id} has no workspace root defined")

        manager = SessionManager(Path(node.workspace_root))
        session = manager.get_or_create(request.session_key)

        dest_path = Path(destination_dir)
        dest_path.mkdir(parents=True, exist_ok=True)

        safe_key = request.session_key.replace(":", "_").replace("/", "_")
        export_file = dest_path / f"export_{node.name}_{safe_key}.jsonl"

        source_path = manager._get_session_path(request.session_key)
        if not source_path.exists():
            raise FileNotFoundError(f"Session transcript not found at {source_path}")

        shutil.copy2(source_path, export_file)

        row = self.repo.insert_agent_session_export(
            node_id=request.node_id,
            session_key=request.session_key,
            export_path=str(export_file),
            messages_count=len(session.messages),
        )

        return SessionExportResponse(
            export_path=row.export_path,
            messages_count=row.messages_count,
            session_key=row.session_key,
            node_id=row.node_id,
        )

    def get_session_summary(self, *, session_key: str) -> UsageSessionSummaryResponse:
        calls = self.repo.list_agent_llm_calls(session_key=session_key)
        if not calls:
            raise ValueError(f"No usage rows found for session '{session_key}'")

        node_ids = {call.node_id for call in calls}
        if len(node_ids) != 1:
            raise ValueError(f"Session '{session_key}' is associated with multiple nodes")

        node_id = next(iter(node_ids))
        node = self.repo.get_node(node_id=node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' not found for session '{session_key}'")

        prompt_tokens = sum(int(call.prompt_tokens or 0) for call in calls)
        completion_tokens = sum(int(call.completion_tokens or 0) for call in calls)
        reasoning_tokens = sum(int(call.reasoning_tokens or 0) for call in calls)
        total_tokens = sum(int(call.total_tokens or 0) for call in calls)
        cost_usd = sum((Decimal(str(call.estimated_cost_usd or 0)) for call in calls), Decimal("0"))

        started_candidates = [call.start_time for call in calls if call.start_time is not None]
        ended_candidates = [call.end_time for call in calls if call.end_time is not None]
        first_call_at = min(started_candidates) if started_candidates else None
        last_call_at = max(ended_candidates) if ended_candidates else (max(started_candidates) if started_candidates else None)
        session_span_seconds = None
        if first_call_at is not None and last_call_at is not None:
            session_span_seconds = max((last_call_at - first_call_at).total_seconds(), 0.0)

        provider_breakdown = Counter(call.provider or "unknown" for call in calls)
        model_breakdown = Counter(call.model or "unknown" for call in calls)

        return UsageSessionSummaryResponse(
            node_id=node.id,
            node_name=node.name,
            session_key=session_key,
            llm_call_count=len(calls),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
            total_tokens=total_tokens,
            cost_usd=round(cost_usd, 10),
            first_call_at=first_call_at,
            last_call_at=last_call_at,
            session_span_seconds=session_span_seconds,
            provider_breakdown=dict(provider_breakdown),
            model_breakdown=dict(model_breakdown),
        )

    def list_recent_sessions(self, *, node_id: str, limit: int = 10) -> UsageRecentSessionsResponse:
        node = self.repo.get_node(node_id=node_id)
        if node is None:
            raise ValueError(f"Node {node_id} not found")

        rows = self.repo.list_recent_session_summaries(node_id=node_id, limit=limit)
        sessions = [
            UsageRecentSessionItem(
                session_key=row["session_key"],
                started_at=row["started_at"],
                ended_at=row["ended_at"],
                llm_call_count=row["llm_call_count"],
                total_tokens=row["total_tokens"],
                cost_usd=float(row["cost_usd"]),
            )
            for row in rows
        ]
        return UsageRecentSessionsResponse(node_id=node.id, node_name=node.name, sessions=sessions)

    def list_retry_state(
        self,
        *,
        node_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> RetryStateResponse:
        items = self.repo.list_agent_task_retries(node_id=node_id, status=status, limit=limit)
        return RetryStateResponse(
            items=[
                RetryStateItem(
                    retry_record_id=item.id,
                    node_id=item.node_id,
                    task_key=item.task_key,
                    session_key=item.session_key,
                    provider=item.provider,
                    model=item.model,
                    status=item.status,
                    failure_class=item.failure_class.value if hasattr(item.failure_class, "value") else str(item.failure_class),
                    attempt_count=item.attempt_count,
                    max_attempts=item.max_attempts,
                    next_attempt_at=item.next_attempt_at,
                    claimed_at=item.claimed_at,
                    completed_at=item.completed_at,
                    last_error_message=item.last_error_message,
                )
                for item in items
            ]
        )

    def get_provider_model_failure_trends(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        limit: int = 50,
    ) -> ProviderModelFailureTrendsResponse:
        rows = self.repo.summarize_llm_failures_by_provider_model(provider=provider, model=model, limit=limit)
        return ProviderModelFailureTrendsResponse(
            items=[
                ProviderModelFailureTrendItem(
                    provider=row["provider"],
                    model=row["model"],
                    failure_class=row["failure_class"],
                    failure_count=row["failure_count"],
                    latest_failure_at=row["latest_failure_at"],
                )
                for row in rows
            ]
        )
