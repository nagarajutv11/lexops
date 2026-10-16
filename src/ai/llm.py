"""Shared model calls. Control paths use temperature=0, except Gemini 3."""

from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Callable
from pathlib import Path

from constants import ROOT

log = logging.getLogger("lexops.llm")

# Gemini 3 at temperature below 1 can loop and leave the extract with no further trace.
_GEMINI_3_LATEST = re.compile(r"^gemini-(?:flash-lite|flash|pro)-latest$")
_CALL_TIMEOUT_SECONDS = 90
_RATE_LIMIT_WAIT_SECONDS = 60
_RATE_LIMIT_RETRIES = 5


class ModelUnavailable(RuntimeError):
    """The model cannot be called. Callers must fail closed."""


def load_env(path: Path | None = None) -> None:
    """Load `.env` once at process start. Variables already set in the environment win."""
    env_path = ROOT / ".env" if path is None else path
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def control_temperature(model: str) -> float | None:
    """Return 0, or None when this model must keep the provider default.

    Gemini 3 models, including ``gemini-flash-latest``, stall or loop when
    temperature is below 1. Omitting it lets the call finish so the next
    extract trace can be written.
    """
    name = model.rsplit("/", 1)[-1].lower()
    if name.startswith("gemini-3") or _GEMINI_3_LATEST.fullmatch(name):
        return None
    return 0


def _failure_text(exc: Exception) -> str:
    text = " ".join(str(exc).split()) or exc.__class__.__name__
    text = re.sub(r"AIza[0-9A-Za-z_\-]{8,}", "REDACTED", text)
    if len(text) > 300:
        text = text[:300] + "..."
    return f"The model call failed. {text}"


def _is_rate_limit(exc: BaseException) -> bool:
    """Gemini 429s arrive as litellm.RateLimitError, sometimes wrapped."""
    seen: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None and current not in seen:
        seen.append(current)
        if current.__class__.__name__ == "RateLimitError":
            return True
        text = str(current).lower()
        if "ratelimiterror" in text or "exceeded your current quota" in text:
            return True
        current = current.__cause__ or current.__context__
    return False


def prepare_client() -> bool:
    """Import LiteLLM on this thread before any request is logged.

    LiteLLM attaches a filter to ``uvicorn.access`` while its own import is
    still running. A deal poll that logs in that window deadlocks on
    ``litellm.types.secret_managers.main``.
    """
    try:
        import litellm.rust_bridge.catalog  # noqa: F401
        import litellm.types.secret_managers.main  # noqa: F401
    except ImportError:
        return False
    return True


def complete(
    messages: list[dict],
    *,
    model: str | None = None,
    json_mode: bool = False,
    on_wait: Callable[[str, str], None] | None = None,
) -> str:
    """One LiteLLM completion. Returns the assistant text, or raises ModelUnavailable.

    A Gemini 429 waits 60 seconds and tries again, up to five times. LiteLLM's
    own immediate retries stay off so a quota error is not hammered.
    """
    load_env()
    if os.environ.get("GOOGLE_API_KEY"):
        os.environ.setdefault("GEMINI_API_KEY", os.environ["GOOGLE_API_KEY"])
    if not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
        raise ModelUnavailable("Set GOOGLE_API_KEY or GEMINI_API_KEY in .env before extracting.")
    if not prepare_client():
        raise ModelUnavailable("Install litellm to call the model.")
    import litellm
    chosen = model or os.environ.get("LLM_MODEL") or os.environ.get("LEXOPS_MODEL") or "gemini/gemini-flash-latest"
    kwargs: dict = {
        "model": chosen,
        "messages": messages,
        "timeout": _CALL_TIMEOUT_SECONDS,
        "num_retries": 0,
    }
    temperature = control_temperature(chosen)
    if temperature is not None:
        kwargs["temperature"] = temperature
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = None
    for attempt in range(_RATE_LIMIT_RETRIES + 1):
        try:
            response = litellm.completion(**kwargs)
            break
        except Exception as exc:
            if _is_rate_limit(exc) and attempt < _RATE_LIMIT_RETRIES:
                detail = (
                    f"Gemini quota exceeded. Waiting {_RATE_LIMIT_WAIT_SECONDS} seconds, "
                    f"then retrying the model call ({attempt + 1} of {_RATE_LIMIT_RETRIES})."
                )
                log.warning(detail)
                if on_wait is not None:
                    on_wait("info", detail)
                time.sleep(_RATE_LIMIT_WAIT_SECONDS)
                continue
            raise ModelUnavailable(_failure_text(exc)) from exc
    if response is None:
        raise ModelUnavailable("The model call failed. The quota retry did not run.")
    content = response.choices[0].message.content if response.choices else ""
    if content is None or not str(content).strip():
        raise ModelUnavailable("The model returned an empty response.")
    return str(content)
