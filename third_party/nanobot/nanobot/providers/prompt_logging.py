from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from loguru import logger

from nanobot.providers.base import LLMRequestContext


_SAFE_SEGMENT = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_segment(value: str | None, *, fallback: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return fallback
    sanitized = _SAFE_SEGMENT.sub("-", raw).strip("-")
    return sanitized or fallback


def write_prompt_log(
    *,
    request_context: LLMRequestContext | None,
    provider_name: str,
    model: str,
    payload: dict[str, Any],
) -> Path | None:
    if request_context is None or not request_context.prompt_logs_root:
        return None

    prompt_logs_root = Path(request_context.prompt_logs_root).expanduser().resolve()
    prompt_logs_root.mkdir(parents=True, exist_ok=True)

    session_dir = prompt_logs_root / _sanitize_segment(request_context.session_key, fallback="no-session")
    session_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = (
        f"{timestamp}-"
        f"{_sanitize_segment(provider_name, fallback='provider')}-"
        f"{_sanitize_segment(request_context.call_source, fallback='call')}-"
        f"{uuid4().hex}.json"
    )
    output_path = session_dir / filename
    document = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider_name,
        "model": model,
        "session_key": request_context.session_key,
        "call_source": request_context.call_source,
        "workspace_root": request_context.workspace_root,
        "runtime_output_root": request_context.runtime_output_root,
        "prompt_logs_root": request_context.prompt_logs_root,
        "node_id": request_context.node_id,
        "node_name": request_context.node_name,
        "payload": payload,
    }

    try:
        output_path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Failed to write prompt log to {}: {}", output_path, exc)
        return None

    return output_path
