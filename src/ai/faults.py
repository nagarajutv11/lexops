"""Fault injection, windowed parsing, and the visible fallback.

A seeded flaky call reproduces connection errors, timeouts, and malformed
payloads. Backoff retries only the transient ones. A remaining failure is
logged and becomes "needs human, parse failed". That result is never
auto-approved, and it keeps the disclaimer.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from ai.reliability import TRANSIENT, CircuitBreaker, call_with_retry
from constants import SHORT_DISCLAIMER

FALLBACK_NOTE = "needs human, parse failed"


@dataclass(frozen=True)
class FaultConfig:
    """Rates that land near a 57% baseline before retries: 0.15 + 0.15 + 0.13."""

    seed: int = 42
    conn_rate: float = 0.15
    timeout_rate: float = 0.15
    malformed_rate: float = 0.13


@dataclass
class FaultLog:
    used_fallback: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def make_flaky(config: FaultConfig | None = None):
    """Return a zero-arg call that fails from the seeded schedule, else 'ok'."""
    chosen = config or FaultConfig()
    rng = random.Random(chosen.seed)
    log = FaultLog()

    def flaky() -> str:
        roll = rng.random()
        if roll < chosen.conn_rate:
            raise ConnectionError("connection reset")
        if roll < chosen.conn_rate + chosen.timeout_rate:
            raise TimeoutError("timeout")
        if roll < chosen.conn_rate + chosen.timeout_rate + chosen.malformed_rate:
            return "not-json"
        return "ok"

    return flaky, log


def is_malformed(value: str) -> bool:
    return value == "not-json"


def run_baseline(n: int, config: FaultConfig | None = None) -> dict:
    flaky, _log = make_flaky(config)
    ok = 0
    malformed = 0
    transient = 0
    for _ in range(n):
        try:
            value = flaky()
        except TRANSIENT:
            transient += 1
            continue
        if is_malformed(value):
            malformed += 1
            continue
        ok += 1
    return {"n": n, "ok": ok, "transient": transient, "malformed": malformed}


def run_with_retry(n: int, config: FaultConfig | None = None, *, attempts: int = 3) -> dict:
    flaky, _log = make_flaky(config)
    ok = 0
    malformed = 0
    failed = 0
    for _ in range(n):
        try:
            value = call_with_retry(flaky, attempts=attempts, sleeper=lambda _seconds: None)
        except TRANSIENT:
            failed += 1
            continue
        if is_malformed(value):
            malformed += 1
            continue
        ok += 1
    return {"n": n, "ok": ok, "failed": failed, "malformed": malformed}


def run_with_fallback(n: int, config: FaultConfig | None = None) -> dict:
    """Caller always receives a result. Fallbacks are logged and not auto-approved."""
    flaky, log = make_flaky(config)
    fallbacks = 0
    for _ in range(n):
        try:
            value = call_with_retry(flaky, attempts=3, sleeper=lambda _seconds: None)
        except TRANSIENT as exc:
            log.used_fallback.append(str(exc))
            fallbacks += 1
            continue
        if is_malformed(value):
            log.used_fallback.append("malformed")
            fallbacks += 1
    return {
        "n": n,
        "fallbacks": fallbacks,
        "logged": len(log.used_fallback),
        "auto_approve": False,
        "disclaimer": SHORT_DISCLAIMER,
        "notice": FALLBACK_NOTE,
    }


def split_windows(text: str, *, window_chars: int = 4000, overlap: int = 200) -> list[str]:
    if window_chars <= overlap:
        raise ValueError("window must be larger than the overlap")
    if len(text) <= window_chars:
        return [text]
    windows = []
    start = 0
    while start < len(text):
        windows.append(text[start : start + window_chars])
        if start + window_chars >= len(text):
            break
        start += window_chars - overlap
    return windows


def parse_in_windows(text: str, parse_one, *, window_chars: int = 4000, overlap: int = 200) -> dict:
    """One timed-out window does not drop the review. A total failure stays human."""
    parsed = []
    errors = []
    for index, window in enumerate(split_windows(text, window_chars=window_chars, overlap=overlap)):
        try:
            parsed.append(parse_one(window))
        except TimeoutError as exc:
            errors.append({"window": index, "error": str(exc)})
    if not parsed:
        return {
            "parse_ok": False,
            "route": "human",
            "auto_approve": False,
            "notice": FALLBACK_NOTE,
            "disclaimer": SHORT_DISCLAIMER,
            "errors": errors,
            "windows": [],
        }
    return {
        "parse_ok": True,
        "route": "review",
        "auto_approve": False,
        "disclaimer": SHORT_DISCLAIMER,
        "errors": errors,
        "windows": parsed,
        "partial": bool(errors),
    }


class GuardedDependency:
    """Breaker around MCP or the model client. Open calls do not reach the dependency."""

    def __init__(self, fn, breaker: CircuitBreaker | None = None) -> None:
        self.fn = fn
        self.breaker = breaker or CircuitBreaker()
        self.calls = 0

    def __call__(self, *args, **kwargs):
        def inner():
            self.calls += 1
            return self.fn(*args, **kwargs)

        return self.breaker.call(inner)
