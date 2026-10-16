"""Retry and circuit breaker from Day 1 Session 2 and Day 4 Session 1.

Tool failures become observations. Retries cover transient errors only.
The breaker opens, then allows one half-open probe after the reset timeout.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

TRANSIENT = (TimeoutError, ConnectionError)


class CircuitOpenError(RuntimeError):
    """The dependency is open. Callers turn this into an observation."""


class ToolFailure(RuntimeError):
    """A non-transient tool failure. The retry loop does not hide it."""


class CircuitBreaker:
    """Closed, open, then half-open. One success in half-open closes it."""

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout: float = 10.0,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._clock = clock or time.monotonic
        self.failures = 0
        self.state = "closed"
        self.opened_at: float | None = None

    def before_call(self) -> None:
        if self.state != "open":
            return
        opened = self.opened_at if self.opened_at is not None else 0.0
        if self._clock() - opened >= self.reset_timeout:
            self.state = "half_open"
            return
        raise CircuitOpenError("circuit open")

    def record_success(self) -> None:
        self.failures = 0
        self.state = "closed"
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.state == "half_open" or self.failures >= self.failure_threshold:
            self.state = "open"
            self.opened_at = self._clock()

    def call(self, fn: Callable[..., T], *args, **kwargs) -> T:
        self.before_call()
        try:
            result = fn(*args, **kwargs)
        except Exception:
            self.record_failure()
            raise
        self.record_success()
        return result


def call_with_retry(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.0,
    sleeper: Callable[[float], None] = time.sleep,
    transient: tuple[type[BaseException], ...] = TRANSIENT,
) -> T:
    """Retry transient errors with exponential backoff. Other errors propagate once."""
    last: BaseException | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except transient as exc:
            last = exc
            if attempt == attempts - 1:
                break
            sleeper(base_delay * (2**attempt))
    assert last is not None
    raise last
