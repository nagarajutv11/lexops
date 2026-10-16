"""LangGraph review. The route is an edge. The envelope send sits after the pause.

State is the product: summary, playbook hits, risk, draft, issues, revision
count, status, and the approver's note. Checkpointing uses SQLite so a paused
review resumes after a new process attaches the same database.
"""

from __future__ import annotations

import operator
import sqlite3
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from ai.policy import MAX_REVISIONS, route_review
from ai.review import draft_redline_text
from ai.scoring import classify_clause, score_clause
from ai.tracing import span, traced
from constants import SHORT_DISCLAIMER

class ReviewState(TypedDict, total=False):
    clause_text: str
    contract_text: str
    counterparty: str
    counterparty_id: str
    agreement_type: str
    raw_source_id: str
    deadline_flag: bool
    summary: dict | None
    parse_ok: bool
    clause_category: str | None
    playbook_hits: list
    citations: list
    retrieved_chunk_ids: list
    playbook_status: str | None
    risk: dict | None
    draft_redline: str
    issues: list
    revision_count: int
    status: str
    approver_note: str
    issue_log: Annotated[list[str], operator.add]
    disclaimer: str
    human_decision: str
    envelope_id: str
    envelope_sent: bool
    redline_indexed: bool
    memory_context: str
    memory_authorizes_auto: bool
    session_id: str
    thread_id: str
    contract_id: str


# Re-exported for tests that inspect the edge function.
__all__ = ["MAX_REVISIONS", "ReviewDeps", "ReviewState", "build_review_graph", "initial_state", "route_review"]


def initial_state(**overrides) -> dict:
    state = {
        "clause_text": "",
        "contract_text": "",
        "counterparty": "",
        "counterparty_id": "",
        "agreement_type": "MSA",
        "raw_source_id": "review",
        "deadline_flag": False,
        "summary": None,
        "parse_ok": True,
        "clause_category": None,
        "playbook_hits": [],
        "citations": [],
        "retrieved_chunk_ids": [],
        "playbook_status": None,
        "risk": None,
        "draft_redline": "",
        "issues": [],
        "revision_count": 0,
        "status": "review",
        "approver_note": "",
        "issue_log": [],
        "disclaimer": SHORT_DISCLAIMER,
        "human_decision": "",
        "envelope_id": "",
        "envelope_sent": False,
        "redline_indexed": False,
        "memory_context": "",
        "memory_authorizes_auto": False,
        "session_id": uuid.uuid4().hex,
        "thread_id": uuid.uuid4().hex,
        "contract_id": "",
    }
    state.update(overrides)
    return state


class EnvelopeBook:
    """Sent envelopes, keyed by thread so a second resume does not send again."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.sent: list[str] = []

    def mark_sent(self, envelope_id: str, thread_id: str) -> bool:
        key = f"{thread_id}:{envelope_id}"
        if self.path is not None:
            existing = self.path.read_text(encoding="utf-8").splitlines() if self.path.is_file() else []
            if key in existing:
                return False
            existing.append(key)
            self.path.write_text("\n".join(existing), encoding="utf-8")
        elif key in self.sent:
            return False
        self.sent.append(key)
        return True


class RedlineBook:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def upsert_redline(self, **kwargs) -> dict:
        self.rows.append(kwargs)
        return kwargs


@dataclass
class ReviewDeps:
    memory: object | None = None
    playbook: object | None = None
    envelopes: EnvelopeBook = field(default_factory=EnvelopeBook)
    redlines: RedlineBook = field(default_factory=RedlineBook)
    complete: object | None = None

    def index_redline(self, state: dict) -> None:
        row = {
            "chunk_id": f"redline::{state.get('thread_id') or 'review'}",
            "text": state.get("draft_redline") or "",
            "clause_category": state.get("clause_category") or "general",
            "counterparty_id": state.get("counterparty_id") or state.get("counterparty") or "",
        }
        self.redlines.upsert_redline(**row)
        upsert = getattr(self.playbook, "upsert_redline", None)
        if upsert is not None and row["counterparty_id"]:
            upsert(**row)


def _extract(state: dict, deps: ReviewDeps) -> dict:
    if state.get("summary"):
        return {}
    category = classify_clause(state.get("clause_text") or "")
    if deps.complete is None:
        return {
            "summary": {"clause_text": state.get("clause_text"), "counterparty": state.get("counterparty")},
            "parse_ok": True,
            "clause_category": category,
        }
    from ai.pipeline import parse_contract

    with span("generation:extract", kind="generation", usage={"session_id": state.get("session_id"), "thread_id": state.get("thread_id")}):
        outcome = parse_contract(
            state.get("contract_text") or state.get("clause_text") or "",
            counterparty=state.get("counterparty") or "",
            agreement_type=state.get("agreement_type") or "MSA",
            raw_source_id=state.get("raw_source_id") or "review",
            complete=deps.complete,
        )
    if outcome.summary is None:
        return {"summary": None, "parse_ok": False, "parse_errors": outcome.errors, "clause_category": None}
    return {"summary": outcome.summary.model_dump(), "parse_ok": True, "clause_category": category}


def _compare(state: dict, deps: ReviewDeps) -> dict:
    if not state.get("parse_ok", True):
        return {
            "risk": {"score": 0, "band": "high", "auto_eligible": False, "in_playbook": False, "category": None},
            "playbook_status": "parse_failed",
            "citations": [],
            "retrieved_chunk_ids": [],
        }
    text = state.get("clause_text") or ""
    with span("retrieve"):
        risk = score_clause(text)
        from ai.review import _citations_for

        citations, retrieved = _citations_for(risk.category)
        with span("rerank"):
            citations = list(citations)
    memory_context = ""
    if deps.memory is not None and state.get("counterparty_id"):
        hits = deps.memory.recall(state["counterparty_id"], text)
        memory_context = "\n".join(hit.text for hit in hits)
    status = "found" if citations else "not_in_playbook"
    return {
        "risk": risk.as_dict(),
        "clause_category": risk.category,
        "citations": citations,
        "retrieved_chunk_ids": retrieved,
        "playbook_hits": citations,
        "playbook_status": status,
        "memory_context": memory_context,
        "memory_authorizes_auto": False,
    }


def _draft(state: dict) -> dict:
    risk = state.get("risk") or {}
    count = int(state.get("revision_count") or 0) + 1
    issues: list[str] = []
    if not state.get("parse_ok", True):
        issues.append("needs human, parse failed")
    elif not risk.get("in_playbook", False):
        issues.append("not in the playbook")
    elif not risk.get("auto_eligible"):
        issues.append("risk above the playbook threshold")
    draft = draft_redline_text(
        counterparty=state.get("counterparty") or "",
        category=risk.get("category"),
        score=float(risk.get("score") or 0),
        band=str(risk.get("band") or "high"),
        citations=list(state.get("citations") or []),
    )
    note = ", ".join(issues) if issues else "clear"
    return {
        "draft_redline": draft,
        "issues": issues,
        "revision_count": count,
        "disclaimer": SHORT_DISCLAIMER,
        "issue_log": [f"rev{count}: {note}"],
    }


def _human(state: dict) -> dict:
    decision = interrupt(
        {
            "deadline_flag": bool(state.get("deadline_flag")),
            "draft": state.get("draft_redline"),
            "risk_score": (state.get("risk") or {}).get("score"),
            "status": "human",
        }
    )
    choice = decision.get("decision", "reject")
    update = {"approver_note": decision.get("note", ""), "human_decision": choice}
    if choice == "edit":
        update["draft_redline"] = decision.get("draft") or state.get("draft_redline")
        update["status"] = "approved"
    elif choice == "approve":
        update["status"] = "approved"
    else:
        update["status"] = "rejected"
    return update


def _approve(state: dict, deps: ReviewDeps) -> dict:
    if not state.get("redline_indexed"):
        deps.index_redline(state)
    return {"status": "auto_approved", "redline_indexed": True, "disclaimer": SHORT_DISCLAIMER}


def _notify(state: dict, deps: ReviewDeps) -> dict:
    """Downstream of the pause. A second pass sees envelope_sent and does nothing."""
    if state.get("envelope_sent"):
        return {}
    envelope_id = state.get("envelope_id") or ""
    if envelope_id:
        deps.envelopes.mark_sent(envelope_id, state.get("thread_id") or "")
    if not state.get("redline_indexed"):
        deps.index_redline(state)
    return {"envelope_sent": True, "redline_indexed": True, "status": "approved", "disclaimer": SHORT_DISCLAIMER}


def _after_human(state: dict) -> str:
    if state.get("status") == "approved":
        return "notify"
    return "end"


def build_review_graph(deps: ReviewDeps | None = None, *, checkpointer=None, trace: bool = False):
    services = deps or ReviewDeps()

    def extract_node(state):
        return _extract(state, services)

    def compare_node(state):
        return _compare(state, services)

    def draft_node(state):
        return _draft(state)

    def human_node(state):
        return _human(state)

    def approve_node(state):
        return _approve(state, services)

    def notify_node(state):
        return _notify(state, services)

    if trace:
        extract_node = traced("extract")(extract_node)
        compare_node = traced("compare")(compare_node)
        draft_node = traced("draft")(draft_node)
        human_node = traced("human")(human_node)
        approve_node = traced("approve")(approve_node)
        notify_node = traced("notify")(notify_node)

    graph = StateGraph(ReviewState)
    graph.add_node("extract", extract_node)
    graph.add_node("compare", compare_node)
    graph.add_node("draft", draft_node)
    graph.add_node("human", human_node)
    graph.add_node("approve", approve_node)
    graph.add_node("notify", notify_node)
    graph.add_edge(START, "extract")
    graph.add_edge("extract", "compare")
    graph.add_edge("compare", "draft")
    graph.add_conditional_edges("draft", route_review, {"redraft": "draft", "auto": "approve", "human": "human"})
    graph.add_conditional_edges("human", _after_human, {"notify": "notify", "end": END})
    graph.add_edge("approve", END)
    graph.add_edge("notify", END)
    return graph.compile(checkpointer=checkpointer if checkpointer is not None else MemorySaver())


def sqlite_checkpointer(path: Path):
    connection = sqlite3.connect(str(path), check_same_thread=False)
    from langgraph.checkpoint.sqlite import SqliteSaver

    saver = SqliteSaver(connection)
    setup = getattr(saver, "setup", None)
    if setup is not None:
        setup()
    return saver, connection
