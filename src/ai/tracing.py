"""Local trace log, with a Langfuse span when the project keys are set.

Tracing records nested retrieve and rerank spans and a generation span per
model call. It does not choose the route. Latency by agent is the event log.
"""

from __future__ import annotations

import contextvars
import functools
import os
import time
from collections.abc import Callable
from contextlib import contextmanager

RUN_EVENTS: list[dict] = []
_STACK: contextvars.ContextVar[tuple[str, ...]] = contextvars.ContextVar("lexops_spans", default=())


def reset_events() -> None:
    RUN_EVENTS.clear()


@contextmanager
def span(name: str, kind: str = "span", usage: dict | None = None):
    parent_stack = _STACK.get()
    parent = parent_stack[-1] if parent_stack else None
    token = _STACK.set(parent_stack + (name,))
    started = time.perf_counter()
    ok = True
    try:
        _langfuse_span(name, kind)
        yield
    except Exception:
        ok = False
        raise
    finally:
        RUN_EVENTS.append(
            {
                "name": name,
                "parent": parent,
                "kind": kind,
                "ms": (time.perf_counter() - started) * 1000,
                "ok": ok,
                "tokens": None if not usage else usage.get("tokens"),
                "cost": None if not usage else usage.get("cost"),
                "session_id": usage.get("session_id") if usage else None,
                "thread_id": usage.get("thread_id") if usage else None,
            }
        )
        _STACK.reset(token)


def traced(role: str):
    """Time one node. Re-raise after the event is stored."""

    def decorator(fn: Callable):
        @functools.wraps(fn)
        def wrapper(state):
            usage = {
                "session_id": state.get("session_id"),
                "thread_id": state.get("thread_id"),
            }
            with span(f"agent:{role}", usage=usage):
                return fn(state)

        return wrapper

    return decorator


def latency_by_agent(events: list[dict] | None = None) -> dict[str, dict]:
    rows = RUN_EVENTS if events is None else events
    grouped: dict[str, list[float]] = {}
    for event in rows:
        name = str(event["name"])
        if not name.startswith("agent:"):
            continue
        grouped.setdefault(name, []).append(float(event["ms"]))
    return {
        name: {"count": len(samples), "avg_ms": sum(samples) / len(samples), "sum_ms": sum(samples)}
        for name, samples in grouped.items()
    }


def _langfuse_span(name: str, kind: str) -> None:
    if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
        return
    try:
        from langfuse import get_client

        client = get_client()
        observation = getattr(client, "start_as_current_observation", None)
        if observation is None:
            return
        with observation(as_type="generation" if kind == "generation" else "span", name=name):
            return
    except Exception:
        return
