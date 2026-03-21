from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionExportRequest(BaseModel):
    node_id: str
    session_key: str


class SessionExportResponse(BaseModel):
    export_path: str
    messages_count: int
    session_key: str
    node_id: str


class LLMCallUsageResponse(BaseModel):
    id: str
    node_id: str
    session_key: str | None
    model: str | None
    provider: str | None
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    start_time: datetime | None
    end_time: datetime | None
    duration_ms: int | None

    model_config = ConfigDict(from_attributes=True)


class UsageSessionSummaryResponse(BaseModel):
    node_id: str
    node_name: str
    session_key: str
    llm_call_count: int
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    total_tokens: int
    cost_usd: float
    first_call_at: datetime | None
    last_call_at: datetime | None
    session_span_seconds: float | None
    provider_breakdown: dict[str, int]
    model_breakdown: dict[str, int]


class UsageRecentSessionItem(BaseModel):
    session_key: str
    started_at: datetime | None
    ended_at: datetime | None
    llm_call_count: int
    total_tokens: int
    cost_usd: float


class UsageRecentSessionsResponse(BaseModel):
    node_id: str
    node_name: str
    sessions: list[UsageRecentSessionItem]


class RetryStateItem(BaseModel):
    retry_record_id: str
    node_id: str
    task_key: str
    session_key: str | None
    provider: str | None
    model: str | None
    status: str
    failure_class: str
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime | None
    claimed_at: datetime | None
    completed_at: datetime | None
    last_error_message: str | None


class RetryStateResponse(BaseModel):
    items: list[RetryStateItem]


class ProviderModelFailureTrendItem(BaseModel):
    provider: str | None
    model: str | None
    failure_class: str
    failure_count: int
    latest_failure_at: datetime | None


class ProviderModelFailureTrendsResponse(BaseModel):
    items: list[ProviderModelFailureTrendItem]
