from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from enum import Enum
import re


class RetryFailureClass(str, Enum):
    TRANSIENT = "transient"
    BUDGET_RECOVERABLE = "budget_recoverable"
    TERMINAL = "terminal"


_TRANSIENT_PATTERNS = (
    re.compile(r"\b429\b"),
    re.compile(r"rate\s*limit", re.IGNORECASE),
    re.compile(r"too many requests", re.IGNORECASE),
    re.compile(r"overloaded", re.IGNORECASE),
    re.compile(r"temporar(?:y|ily) unavailable", re.IGNORECASE),
    re.compile(r"timeout", re.IGNORECASE),
    re.compile(r"connection reset", re.IGNORECASE),
    re.compile(r"service unavailable", re.IGNORECASE),
    re.compile(r"bad gateway", re.IGNORECASE),
)

_BUDGET_PATTERNS = (
    re.compile(r"insufficient credits?", re.IGNORECASE),
    re.compile(r"insufficient balance", re.IGNORECASE),
    re.compile(r"quota exceeded", re.IGNORECASE),
    re.compile(r"budget exceeded", re.IGNORECASE),
    re.compile(r"payment required", re.IGNORECASE),
    re.compile(r"credit balance", re.IGNORECASE),
)

_TERMINAL_PATTERNS = (
    re.compile(r"invalid api key", re.IGNORECASE),
    re.compile(r"authentication", re.IGNORECASE),
    re.compile(r"unauthorized", re.IGNORECASE),
    re.compile(r"forbidden", re.IGNORECASE),
    re.compile(r"unsupported model", re.IGNORECASE),
    re.compile(r"model .* does not exist", re.IGNORECASE),
    re.compile(r"invalid request", re.IGNORECASE),
    re.compile(r"malformed", re.IGNORECASE),
)


@dataclass(frozen=True, slots=True)
class RetryDecision:
    failure_class: RetryFailureClass
    retryable: bool
    next_attempt_at: datetime | None
    delay_seconds: int | None
    max_attempts: int
    reason: str


TRANSIENT_DELAYS_SECONDS = (60, 300, 900, 3600, 21600)
BUDGET_DELAY_FALLBACK_HOURS = (6, 12, 24)
MAX_ATTEMPTS = 8


def classify_llm_failure(message: str | None) -> RetryFailureClass:
    text = (message or "").strip()
    if not text:
        return RetryFailureClass.TRANSIENT

    for pattern in _BUDGET_PATTERNS:
        if pattern.search(text):
            return RetryFailureClass.BUDGET_RECOVERABLE
    for pattern in _TERMINAL_PATTERNS:
        if pattern.search(text):
            return RetryFailureClass.TERMINAL
    for pattern in _TRANSIENT_PATTERNS:
        if pattern.search(text):
            return RetryFailureClass.TRANSIENT
    return RetryFailureClass.TRANSIENT


def compute_retry_decision(
    *,
    attempt_count: int,
    failure_class: RetryFailureClass,
    now: datetime | None = None,
    reset_time_utc: str | None = None,
) -> RetryDecision:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    if attempt_count >= MAX_ATTEMPTS or failure_class == RetryFailureClass.TERMINAL:
        return RetryDecision(
            failure_class=failure_class,
            retryable=False,
            next_attempt_at=None,
            delay_seconds=None,
            max_attempts=MAX_ATTEMPTS,
            reason="max attempts reached" if attempt_count >= MAX_ATTEMPTS else "terminal failure",
        )

    if failure_class == RetryFailureClass.TRANSIENT:
        delay_seconds = TRANSIENT_DELAYS_SECONDS[min(attempt_count, len(TRANSIENT_DELAYS_SECONDS) - 1)]
        return RetryDecision(
            failure_class=failure_class,
            retryable=True,
            next_attempt_at=current_time + timedelta(seconds=delay_seconds),
            delay_seconds=delay_seconds,
            max_attempts=MAX_ATTEMPTS,
            reason="transient backoff",
        )

    delay_seconds = _compute_budget_delay_seconds(attempt_count=attempt_count, now=current_time, reset_time_utc=reset_time_utc)
    return RetryDecision(
        failure_class=failure_class,
        retryable=True,
        next_attempt_at=current_time + timedelta(seconds=delay_seconds),
        delay_seconds=delay_seconds,
        max_attempts=MAX_ATTEMPTS,
        reason="budget recovery backoff",
    )


def _compute_budget_delay_seconds(*, attempt_count: int, now: datetime, reset_time_utc: str | None) -> int:
    reset_delay = _delay_until_next_reset(now=now, reset_time_utc=reset_time_utc)
    fallback_hours = BUDGET_DELAY_FALLBACK_HOURS[min(attempt_count, len(BUDGET_DELAY_FALLBACK_HOURS) - 1)]
    fallback_delay = int(timedelta(hours=fallback_hours).total_seconds())
    if reset_delay is None:
        return fallback_delay
    return max(reset_delay, fallback_delay)


def _delay_until_next_reset(*, now: datetime, reset_time_utc: str | None) -> int | None:
    raw = (reset_time_utc or "").strip()
    if not raw:
        return None
    try:
        hour_text, minute_text = raw.split(":", 1)
        reset_clock = time(hour=int(hour_text), minute=int(minute_text))
    except (TypeError, ValueError):
        return None

    candidate = datetime.combine(now.date(), reset_clock, tzinfo=timezone.utc)
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return max(int((candidate - now).total_seconds()), 0)
