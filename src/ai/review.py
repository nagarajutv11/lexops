"""The review pipeline the API, the eval harness, and the agents share."""

from __future__ import annotations

from ai.guardrails import ReviewDecision, apply_guardrails
from intake import deadline_flag_for
from ai.scoring import CATEGORY_SLUG, classify_clause, score_clause
from constants import SHORT_DISCLAIMER
from records import load_playbook_section


def draft_redline_text(*, counterparty: str, category: str | None, score: float, band: str, citations: list[str]) -> str:
    cite = ", ".join(citations) if citations else "none"
    return "\n".join(
        [
            f"Suggested markup for {counterparty}.",
            f"Clause category: {category or 'unmapped'}.",
            f"Risk score: {score:.0f}. Band: {band}.",
            f"Citations: {cite}.",
            "Align the language with the cited playbook position.",
            SHORT_DISCLAIMER,
        ]
    )


def _citations_for(category: str | None) -> tuple[list[str], list[str]]:
    slug = CATEGORY_SLUG.get(category or "")
    if not slug:
        return [], []
    section = load_playbook_section(slug)
    retrieved = list(section.chunk_ids)
    cited = [
        chunk_id
        for chunk_id in retrieved
        if "::preferred" in chunk_id or "::fallback" in chunk_id or "::walk_away" in chunk_id
    ]
    return cited, retrieved


def run_review(
    *,
    counterparty: str,
    clause_text: str,
    request_text: str = "",
    agreement_type: str = "MSA",
    deadline_flag: bool | None = None,
    parse_ok: bool = True,
    record_id: str = "",
) -> ReviewDecision:
    """Score, cite the playbook section, draft, and guard. No model call."""
    del agreement_type, record_id
    flag = deadline_flag_for(request_text) if deadline_flag is None else deadline_flag
    if not parse_ok:
        return apply_guardrails(
            draft=f"Needs human, parse failed. {SHORT_DISCLAIMER}",
            risk_score=0,
            risk_band="high",
            clause_category=None,
            parse_ok=False,
            deadline_flag=flag,
            in_playbook=False,
            auto_eligible=False,
            citations=[],
            retrieved_chunk_ids=[],
            counterparty=counterparty,
            user_text=f"{request_text}\n{clause_text}",
            retrieved_texts=[],
        )
    category = classify_clause(clause_text)
    risk = score_clause(clause_text, category=category)
    citations, retrieved = _citations_for(category)
    draft = draft_redline_text(
        counterparty=counterparty,
        category=category,
        score=risk.score,
        band=risk.band,
        citations=citations,
    )
    return apply_guardrails(
        draft=draft,
        risk_score=risk.score,
        risk_band=risk.band,
        clause_category=category,
        parse_ok=True,
        deadline_flag=flag,
        in_playbook=risk.in_playbook,
        auto_eligible=risk.auto_eligible,
        citations=citations,
        retrieved_chunk_ids=retrieved,
        counterparty=counterparty,
        user_text=f"{request_text}\n{clause_text}",
        retrieved_texts=[],
    )
