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
