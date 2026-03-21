from __future__ import annotations

import ipaddress
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


_HOSTNAME_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?!-)(?:[A-Za-z0-9-]{1,63}\.)*[A-Za-z0-9-]{1,63}(?<!-)$"
)


class RuntimeActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "gateway_start",
        "gateway_stop",
        "gateway_status",
        "list_agents",
        "invoke_prompt",
        "process_due_retries",
        "retry_now",
        "cancel_retry",
    ]
    node_id: str | None = None
    node_name: str | None = None
    gateway_host: str = "127.0.0.1"
    gateway_port: int = Field(default=18790, ge=1, le=65535)
    force_restart: bool = False
    prompt: str | None = None
    session_key: str = "cli:verification"
    markdown: bool = False
    include_logs: bool = False
    task_key: str | None = None

    @field_validator("gateway_host")
    @classmethod
    def validate_gateway_host(cls, value: str) -> str:
        raw = value.strip()
        if not raw:
            raise ValueError("gateway_host must not be empty")
        try:
            ipaddress.ip_address(raw)
            return raw
        except ValueError:
            pass
        if not _HOSTNAME_PATTERN.fullmatch(raw):
            raise ValueError("gateway_host must be a valid IP address or hostname")
        return raw

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("prompt must not be empty when provided")
        if len(stripped) > 8000:
            raise ValueError("prompt must be <= 8000 characters")
        return stripped

    @field_validator("task_key")
    @classmethod
    def validate_task_key(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("task_key must not be empty when provided")
        if len(stripped) > 255:
            raise ValueError("task_key must be <= 255 characters")
        return stripped
