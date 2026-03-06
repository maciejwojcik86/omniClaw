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

    action: Literal["gateway_start", "gateway_stop", "gateway_status", "list_agents"]
    node_id: str | None = None
    node_name: str | None = None
    gateway_host: str = "127.0.0.1"
    gateway_port: int = Field(default=18790, ge=1, le=65535)
    force_restart: bool = False

    @field_validator("gateway_host")
    @classmethod
    def validate_gateway_host(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("gateway_host must not be empty")
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            pass
        if not _HOSTNAME_PATTERN.fullmatch(candidate):
            raise ValueError("gateway_host must be a valid IP address or hostname")
        return candidate
