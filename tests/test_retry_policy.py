from datetime import datetime, timezone

from omniclaw.runtime.retry_policy import (
    RetryFailureClass,
    classify_llm_failure,
    compute_retry_decision,
)


def test_classify_llm_failure_transient() -> None:
    assert classify_llm_failure("429 Too Many Requests from provider") == RetryFailureClass.TRANSIENT
    assert classify_llm_failure("upstream overloaded") == RetryFailureClass.TRANSIENT


def test_classify_llm_failure_budget_recoverable() -> None:
    assert classify_llm_failure("insufficient credits on account") == RetryFailureClass.BUDGET_RECOVERABLE
    assert classify_llm_failure("quota exceeded until billing reset") == RetryFailureClass.BUDGET_RECOVERABLE


def test_classify_llm_failure_terminal() -> None:
    assert classify_llm_failure("invalid api key") == RetryFailureClass.TERMINAL
    assert classify_llm_failure("unsupported model requested") == RetryFailureClass.TERMINAL


def test_compute_retry_decision_transient_progressive_backoff() -> None:
    now = datetime(2026, 3, 19, 9, 0, tzinfo=timezone.utc)
    first = compute_retry_decision(attempt_count=0, failure_class=RetryFailureClass.TRANSIENT, now=now)
    second = compute_retry_decision(attempt_count=1, failure_class=RetryFailureClass.TRANSIENT, now=now)
    assert first.retryable is True
    assert second.retryable is True
    assert first.delay_seconds == 60
    assert second.delay_seconds == 300
    assert second.next_attempt_at > first.next_attempt_at


def test_compute_retry_decision_budget_uses_long_delay_and_reset_time() -> None:
    now = datetime(2026, 3, 19, 9, 0, tzinfo=timezone.utc)
    decision = compute_retry_decision(
        attempt_count=0,
        failure_class=RetryFailureClass.BUDGET_RECOVERABLE,
        now=now,
        reset_time_utc="18:00",
    )
    assert decision.retryable is True
    assert decision.delay_seconds == 9 * 3600
    assert decision.next_attempt_at == datetime(2026, 3, 19, 18, 0, tzinfo=timezone.utc)


def test_compute_retry_decision_terminal_or_exhausted_stops_retrying() -> None:
    now = datetime(2026, 3, 19, 9, 0, tzinfo=timezone.utc)
    terminal = compute_retry_decision(attempt_count=0, failure_class=RetryFailureClass.TERMINAL, now=now)
    exhausted = compute_retry_decision(attempt_count=99, failure_class=RetryFailureClass.TRANSIENT, now=now)
    assert terminal.retryable is False
    assert terminal.next_attempt_at is None
    assert exhausted.retryable is False
    assert exhausted.next_attempt_at is None
