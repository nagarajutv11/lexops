"""Output guardrails. Day 4 Session 2 checks, applied to a LexOps decision.

The disclaimer is forced on. Auto-approval stops for risk, a failed parse,
injection, or a closing deadline. Banned legal conclusions are rejected.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from ai.summary import BANNED_PHRASES
from constants import SHORT_DISCLAIMER

_INJECTION_RE = re.compile(
    r"ignore (all )?(previous|prior|above) instructions|"
    r"ignore all prior|"
    r"system update\s*:|"
    r"you are now|"
    r"new policy\s*:|"
    r"jailbreak",
    re.IGNORECASE,
)


def detect_prompt_injection(text: str) -> bool:
    return bool(_INJECTION_RE.search(text or ""))


class ReviewDecision(BaseModel):
    """The result a caller is allowed to keep."""

    model_config = ConfigDict(extra="ignore")

    route: Literal["auto", "human", "rejected"]
    disclaimer: str
    risk_score: float
    risk_band: Literal["low", "medium", "high"]
    clause_category: str | None = None
    parse_ok: bool = True
    injection: bool = False
    deadline_flag: bool = False
    in_playbook: bool = False
    draft: str
    citations: list[str] = []
    retrieved_chunk_ids: list[str] = []
    flags: list[str] = []
    counterparty: str = ""

    @field_validator("disclaimer")
    @classmethod
    def force_disclaimer(cls, _value: str) -> str:
        return SHORT_DISCLAIMER


def _banned(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in BANNED_PHRASES)


def apply_guardrails(
    *,
    draft: str,
    risk_score: float,
    risk_band: str,
    clause_category: str | None,
    parse_ok: bool,
    deadline_flag: bool,
    in_playbook: bool,
    auto_eligible: bool,
    citations: list[str],
    retrieved_chunk_ids: list[str],
    counterparty: str,
    user_text: str,
    retrieved_texts: list[str] | None = None,
) -> ReviewDecision:
    flags: list[str] = []
    injection = detect_prompt_injection(user_text)
    if injection:
        flags.append("prompt_injection_in_user_input")
    for chunk in retrieved_texts or []:
        if detect_prompt_injection(chunk):
            injection = True
            flags.append("prompt_injection_in_retrieved_content")
            break
    if any(chunk_id not in set(retrieved_chunk_ids) for chunk_id in citations):
        flags.append("citation_outside_retrieved_set")
    route: Literal["auto", "human", "rejected"] = "auto" if auto_eligible and parse_ok and in_playbook else "human"
    if risk_score < 85:
        flags.append("risk_above_threshold")
        route = "human"
    if not parse_ok:
        flags.append("parse_failed")
        route = "human"
    if not in_playbook:
        flags.append("not_in_playbook")
        route = "human"
    if injection:
        route = "human"
    if deadline_flag and route == "auto":
        flags.append("deadline_pressure")
        route = "human"
    if flags.count("citation_outside_retrieved_set"):
        route = "human"
    text = draft
    if _banned(text):
        flags.append("banned_phrase")
        text = f"Rejected. The draft contained a legal conclusion. {SHORT_DISCLAIMER}"
        route = "rejected"
    elif SHORT_DISCLAIMER not in text:
        text = f"{text.rstrip()}\n{SHORT_DISCLAIMER}"
    return ReviewDecision(
        route=route,
        disclaimer=SHORT_DISCLAIMER,
        risk_score=risk_score,
        risk_band=risk_band,  # type: ignore[arg-type]
        clause_category=clause_category,
        parse_ok=parse_ok,
        injection=injection,
        deadline_flag=deadline_flag,
        in_playbook=in_playbook,
        draft=text,
        citations=list(citations),
        retrieved_chunk_ids=list(retrieved_chunk_ids),
        flags=flags,
        counterparty=counterparty,
    )
