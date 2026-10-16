"""Supervised review team. Specialists do not write each other's keys.

The supervisor may suggest a route. ``authorize_route`` is what allows it.
Contract and envelope reads go through the MCP client and nowhere else.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ai.guardrails import apply_guardrails
from ai.policy import authorize_route, enforce_scope, supervisor_policy
from ai.review import draft_redline_text
from ai.scoring import score_clause
from constants import SHORT_DISCLAIMER
from contracts_mcp import McpContractClient

_OFFLINE = object()


class TeamState(TypedDict, total=False):
    clause_text: str
    contract_text: str
    counterparty: str
    counterparty_id: str
    agreement_type: str
    raw_source_id: str
    contract_id: str
    deadline_flag: bool
    parse_ok: bool
    parse_errors: list
    records_loaded: bool
    hops: int
    summary: dict | None
    clause_category: str | None
    playbook_status: str | None
    playbook_hits: list
    draft_redline: str
    disclaimer: str
    citations: list
    retrieved_chunk_ids: list
    issues: list
    risk: dict | None
    legal_review: dict | None
    revision_count: int
    log: Annotated[list[str], operator.add]
    status: str
    suggested_route: str
    contract_record: dict
    envelope: dict


def _load(state: dict, gateway) -> dict:
    matches = gateway.call("search_contracts", {"counterparty_id": state.get("counterparty_id") or ""})
    envelopes = gateway.call("list_envelopes", {})
    text = None
    if state.get("contract_id"):
        text = gateway.call("read_contract", {"relative_path": f"{state['contract_id']}.txt"})
    return {"contract_record": {"matches": matches, "text": text}, "envelope": envelopes}


def extraction_node(state: dict, *, complete=_OFFLINE, on_step=None) -> dict:
    """Read the contract. Offline callers keep the stub summary and do not call a model."""
    text = state.get("contract_text") or state.get("clause_text") or ""
    from ai.scoring import classify_clause

    if complete is _OFFLINE:
        return enforce_scope(
            "extraction",
            {
                "summary": {"clause_text": text, "counterparty": state.get("counterparty")},
                "clause_category": classify_clause(text),
                "parse_ok": bool(state.get("parse_ok", True)),
                "parse_errors": [],
                "log": ["extraction"],
            },
        )
    from ai.pipeline import parse_contract

    outcome = parse_contract(
        text,
        counterparty=state.get("counterparty") or "",
        agreement_type=state.get("agreement_type") or "MSA",
        raw_source_id=state.get("raw_source_id") or "review",
        complete=complete,
        on_step=on_step,
    )
    if outcome.summary is None:
        return enforce_scope(
            "extraction",
            {
                "summary": None,
                "clause_category": None,
                "parse_ok": False,
                "parse_errors": outcome.errors,
                "log": ["extraction"],
            },
        )
    return enforce_scope(
        "extraction",
        {
            "summary": outcome.summary.model_dump(),
            "clause_category": classify_clause(text),
            "parse_ok": True,
            "parse_errors": [],
            "log": ["extraction"],
        },
    )


def playbook_node(state: dict) -> dict:
    from ai.review import _citations_for

    category = state.get("clause_category")
    citations, retrieved = _citations_for(category)
    status = "found" if citations else "not_in_playbook"
    return enforce_scope(
        "playbook",
        {
            "playbook_hits": citations,
            "citations": citations,
            "retrieved_chunk_ids": retrieved,
            "playbook_status": status,
            "log": ["playbook"],
        },
    )


def redline_node(state: dict) -> dict:
    risk = score_clause(state.get("clause_text") or "", category=state.get("clause_category"))
    draft = draft_redline_text(
        counterparty=state.get("counterparty") or "",
        category=risk.category,
        score=risk.score,
        band=risk.band,
        citations=list(state.get("citations") or []),
    )
    return enforce_scope(
        "redline",
        {"draft_redline": draft, "disclaimer": SHORT_DISCLAIMER, "log": ["redline"]},
    )


def legal_node(state: dict) -> dict:
    risk = score_clause(state.get("clause_text") or "", category=state.get("clause_category"))
    issues: list[str] = []
    retrieved = set(state.get("retrieved_chunk_ids") or [])
    if any(chunk_id not in retrieved for chunk_id in state.get("citations") or []):
        issues.append("citation outside the retrieved set")
    draft = state.get("draft_redline") or ""
    if SHORT_DISCLAIMER not in draft:
        issues.append("disclaimer missing")
    if f"Risk score: {risk.score:.0f}" not in draft:
        issues.append("draft risk does not match the calculator")
    if not risk.auto_eligible:
        issues.append("non-standard")
    return enforce_scope(
        "legal",
        {
            "issues": issues,
            "risk": risk.as_dict(),
            "legal_review": {
                "structure_ok": bool(draft),
                "complete": bool(state.get("summary")),
                "risk_score": risk.score,
                "authority": False,
            },
            "log": ["legal"],
        },
    )


def build_team_graph(gateway=None, *, checkpointer=None, complete=_OFFLINE, on_extract_step=None):
    client = gateway or McpContractClient()

    def supervisor(state: dict) -> dict:
        hops = int(state.get("hops") or 0) + 1
        if hops > 8:
            return enforce_scope(
                "supervisor",
                {"hops": hops, "suggested_route": "human", "status": "human", "log": ["cap"]},
            )
        update: dict = {"hops": hops}
        if not state.get("records_loaded"):
            update.update(_load(state, client))
            update["records_loaded"] = True
        nxt = supervisor_policy({**state, **update})
        if nxt in {"auto", "human"}:
            nxt = authorize_route(nxt, {**state, **update})
        update["suggested_route"] = nxt
        update["log"] = [nxt]
        return enforce_scope("supervisor", update)

    def finish(state: dict) -> dict:
        risk = state.get("risk") or {}
        decision = apply_guardrails(
            draft=state.get("draft_redline") or "",
            risk_score=float(risk.get("score") or 0),
            risk_band=str(risk.get("band") or "high"),
            clause_category=state.get("clause_category"),
            parse_ok=bool(state.get("parse_ok", True)),
            deadline_flag=bool(state.get("deadline_flag")),
            in_playbook=bool(risk.get("in_playbook")),
            auto_eligible=bool(risk.get("auto_eligible")) and not state.get("issues"),
            citations=list(state.get("citations") or []),
            retrieved_chunk_ids=list(state.get("retrieved_chunk_ids") or []),
            counterparty=state.get("counterparty") or "",
            user_text=state.get("clause_text") or "",
        )
        return enforce_scope(
            "supervisor",
            {"status": decision.route, "suggested_route": decision.route, "log": [f"finish:{decision.route}"]},
        )

    def route(state: dict) -> str:
        suggested = state.get("suggested_route") or "human"
        if suggested in {"extraction", "playbook", "redline", "legal"}:
            return suggested
        return "finish"

    def extract(state: dict) -> dict:
        return extraction_node(state, complete=complete, on_step=on_extract_step)

    graph = StateGraph(TeamState)
    graph.add_node("supervisor", supervisor)
    graph.add_node("extraction", extract)
    graph.add_node("playbook", playbook_node)
    graph.add_node("redline", redline_node)
    graph.add_node("legal", legal_node)
    graph.add_node("finish", finish)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route,
        {
            "extraction": "extraction",
            "playbook": "playbook",
            "redline": "redline",
            "legal": "legal",
            "finish": "finish",
        },
    )
    for name in ("extraction", "playbook", "redline", "legal"):
        graph.add_edge(name, "supervisor")
    graph.add_edge("finish", END)
    return graph.compile(checkpointer=checkpointer or MemorySaver())


def team_input(**overrides) -> dict:
    state = {
        "clause_text": "",
        "contract_text": "",
        "counterparty": "",
        "counterparty_id": "",
        "agreement_type": "MSA",
        "raw_source_id": "review",
        "contract_id": "",
        "deadline_flag": False,
        "parse_ok": True,
        "parse_errors": [],
        "records_loaded": False,
        "hops": 0,
        "summary": None,
        "clause_category": None,
        "playbook_status": None,
        "draft_redline": "",
        "citations": [],
        "retrieved_chunk_ids": [],
        "issues": [],
        "risk": None,
        "legal_review": None,
        "revision_count": 0,
        "log": [],
        "status": "review",
        "suggested_route": "",
    }
    state.update(overrides)
    return state
