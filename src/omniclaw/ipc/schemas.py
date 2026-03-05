from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IpcActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["scan_messages", "scan_forms"]
    limit: int = Field(default=200, ge=1, le=2000)
