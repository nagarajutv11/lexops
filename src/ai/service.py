"""LexOps AI. Every deal change comes through here. Reads stay on the store.

Creating a deal stores the pasted clause and returns. Extraction starts
after that save. Later review changes are recorded here as well. Model
calls live in this folder.
"""

from __future__ import annotations

import logging

from ai.guardrails import apply_guardrails
from ai.pipeline import FIELD_LABELS
from ai.review import _citations_for, draft_redline_text
from ai.scoring import CATEGORY_SLUG, classify_clause, score_clause
from ai.team import build_team_graph, team_input
from records import RecordNotFound, load_playbook_section
from store import Store

log = logging.getLogger("lexops.ai")


class LexopsAI:
    def __init__(self, store: Store, complete=None) -> None:
        self.store = store
        self.complete = complete

    def create_deal(
        self,
        *,
        customer: str,
        contract_type: str,
        contract_text: str,
    ) -> dict:
        """Save the pasted clause. This does not call the model."""
        deal = self.store.create_deal(
            customer=customer,
            contract_type=contract_type,
            contract_text=contract_text,
        )
        self._trace(
            deal["id"],
            "saved",
            f"Saved {deal['customer']} {deal['contract_type']}. Extraction starts after the deal page opens.",
            level="info",
        )
        return self.store.get_deal(deal["id"])

    def extract_saved_deal(self, deal_id: int) -> None:
        """Read the stored clause and write the extract. Safe to run after the response."""
        try:
            deal = self.store.get_deal(deal_id)
        except Exception:
            log.exception("Deal %s is not in the database, so extraction did not start.", deal_id)
            return
        if deal["round"].get("extracted"):
            return
        round_number = deal["round"]["round_number"]
        text = deal["round"]["contract_text"]
        source_id = f"deal-{deal['id']}-round-{round_number}"
        self._trace(deal_id, "extracting", "Extraction started.", level="info")
        self._trace(deal_id, "extracting", "Supervisor asked the extraction agent to read the contract.", level="info")

        def on_step(level: str, detail: str) -> None:
            self._trace(deal_id, "extracting", detail, level=level)

        try:
            graph = build_team_graph(complete=self.complete, on_extract_step=on_step)
            result = graph.invoke(
                team_input(
                    clause_text=text,
                    contract_text=text,
                    counterparty=deal["customer"],
                    counterparty_id=deal["counterparty_id"],
                    agreement_type=deal["contract_type"],
                    raw_source_id=source_id,
                ),
                config={"configurable": {"thread_id": source_id}},
            )
        except Exception as exc:
            self._trace(deal_id, "extracting", f"Extraction failed. {exc}", level="error")
            self.store.record_extraction(deal_id, _error_panel([{"field": "model", "error": str(exc)}]), ok=False)
            self._trace(deal_id, "end", "END. Extraction failed.", level="info")
            return
        if not result.get("parse_ok", True):
            self.store.record_extraction(deal_id, _error_panel(result.get("parse_errors") or []), ok=False)
            self._trace(
                deal_id,
                "checking_playbook",
                "Parse failed. The supervisor did not send this extract to Playbook.",
                level="error",
            )
            self._trace(deal_id, "end", "END. Parse failed.", level="info")
            return
        self.store.record_extraction(deal_id, _summary_panel(result.get("summary") or {}), ok=True)
        status, rows = _playbook_rows(result)
        self.store.record_playbook(deal_id, playbook=rows, playbook_status=status)
        self.complete_review(deal_id)

    def complete_review(self, deal_id: int) -> dict | None:
        """Score the stored clause, write the redline and memo, and leave review.

        Safe to call again. A round that is no longer in review is left as it is.
        """
        try:
            deal = self.store.get_deal(deal_id)
        except Exception:
            log.exception("Deal %s is not in the database, so the review was not finished.", deal_id)
            return None
        rnd = deal["round"]
        if rnd["status"] != "in_review" or not rnd.get("extracted") or not rnd.get("playbook_status") or rnd.get("redline"):
            return None
        text = rnd["contract_text"]
        category = classify_clause(text)
        risk = score_clause(text, category=category)
        citations, retrieved = _citations_for(category)
        draft = draft_redline_text(
            counterparty=deal["customer"],
            category=category,
            score=risk.score,
            band=risk.band,
            citations=citations,
        )
        issues = [] if risk.auto_eligible else ["non-standard"]
        decision = apply_guardrails(
            draft=draft,
            risk_score=risk.score,
            risk_band=risk.band,
            clause_category=category,
            parse_ok=True,
            deadline_flag=False,
            in_playbook=risk.in_playbook and rnd.get("playbook_status") == "found",
            auto_eligible=risk.auto_eligible and not issues,
            citations=citations,
            retrieved_chunk_ids=retrieved,
            counterparty=deal["customer"],
            user_text=text,
        )
        score = int(decision.risk_score)
        needs_ceo = score < 50
        liability = category == "liability_cap" and decision.route != "auto"
        if decision.injection:
            status, path = "blocked", "counsel"
        elif decision.route == "rejected":
            status, path = "rejected", "counsel"
        elif needs_ceo:
            status, path = "blocked", "counsel"
        elif decision.route == "auto":
            status, path = "approved", "auto"
        else:
            status, path = "waiting_on_counsel", "counsel"
        if needs_ceo:
            tier, days = 3, 5
        elif liability or score < 85:
            tier, days = 2, 3
        else:
            tier, days = 1, 2
        reason = _route_reason(status, score=score, band=decision.risk_band, injection=decision.injection)
        return self.store.record_review(
            deal_id,
            redline=decision.draft,
            score=score,
            band=decision.risk_band,
            tier=tier,
            turnaround_days=days,
            status=status,
            path=path,
            route_reason=reason,
            injection=decision.injection,
            liability_cap_redline=liability,
            needs_ceo=needs_ceo,
        )

    def _trace(self, deal_id: int, step: str, detail: str, *, level: str) -> None:
        if level == "error":
            log.error("deal %s | %s | %s", deal_id, step, detail)
        else:
            log.info("deal %s | %s | %s", deal_id, step, detail)
        try:
            self.store.add_trace(deal_id, step, detail, level=level)
        except Exception:
            log.exception("Could not store a trace for deal %s.", deal_id)

    def add_round(self, deal_id: int, *, contract_text: str) -> dict:
        return self.store.add_round(deal_id, contract_text=contract_text)

    def edit_redline(self, deal_id: int, *, redline_text: str, liability_cap_redline: bool) -> dict:
        return self.store.edit_redline(
            deal_id,
            redline_text=redline_text,
            liability_cap_redline=liability_cap_redline,
        )

    def approve(self, deal_id: int) -> dict:
        return self.store.approve(deal_id)

    def request_changes(self, deal_id: int) -> dict:
        return self.store.request_changes(deal_id)

    def reject(self, deal_id: int) -> dict:
        return self.store.reject(deal_id)

    def ceo_signoff(self, deal_id: int) -> dict:
        return self.store.ceo_signoff(deal_id)


def _route_reason(status: str, *, score: int, band: str, injection: bool) -> str:
    if injection:
        return "Prompt injection was detected. Stopped before a decision."
    if status == "approved":
        return f"Score {score}, {band}. Standard language. Auto-approved."
    if status == "blocked":
        return f"Score {score}, {band}. The score is below 50. CEO sign-off is required before a decision."
    if status == "rejected":
        return "The draft contained a legal conclusion. Rejected."
    return f"Score {score}, {band}. Left for counsel."


def _error_panel(errors: list) -> dict:
    rows = errors or [{"field": "summary", "error": "Nothing was extracted."}]
    return {
        "extracted": True,
        "raw_json": "",
        "extraction": [{"field": item.get("field", "summary"), "value": "", "error": item.get("error", "")} for item in rows],
        "clauses": [],
        "errors": rows,
    }


def _summary_panel(summary: dict) -> dict:
    return {
        "extracted": True,
        "raw_json": "",
        "extraction": [
            {"field": label, "value": summary.get(key, ""), "error": None}
            for key, label in FIELD_LABELS
        ],
        "clauses": summary.get("clauses") or [],
        "errors": [],
        "summary": summary,
    }


def _playbook_rows(state: dict) -> tuple[str, list]:
    status = state.get("playbook_status") or "not_in_playbook"
    slug = CATEGORY_SLUG.get(state.get("clause_category") or "")
    if status != "found" or not slug:
        return "not_in_playbook", []
    try:
        section = load_playbook_section(slug)
    except RecordNotFound:
        return "not_in_playbook", []
    citations = list(state.get("citations") or [])
    chunk_id = citations[0] if citations else (section.chunk_ids[0] if section.chunk_ids else "")
    return "found", [
        {
            "family": section.title,
            "preferred": section.preferred,
            "fallback": section.fallback,
            "walk_away": section.walk_away,
            "citation_title": section.title,
            "chunk_id": chunk_id,
        }
    ]
