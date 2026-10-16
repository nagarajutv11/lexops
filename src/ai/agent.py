"""One tool-calling agent for a clause. Day 1 Session 2 loop, LexOps tools.

The model chooses the calls. The memo file contains the tool results. The loop
stops when the model stops calling tools or the iteration cap is reached.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ai.summary import ContractSummary
from ai.tools import ToolKit

SYSTEM_PROMPT = (
    "You review one contract clause for Northwind Systems. "
    "Call clause_risk_calculator, renewal_date_calendar, and summary_memo_writer. "
    "Use the tool results for every number. "
    "Do not say a clause is enforceable or unenforceable. "
    "Do not give authorized legal advice and do not say anyone should sign."
)


@dataclass
class ModelTurn:
    content: str = ""
    tool_calls: list[dict] = field(default_factory=list)


@dataclass
class AgentRun:
    content: str
    observations: list[str]
    iterations: int
    memo_path: str | None


def run_clause_agent(
    summary: ContractSummary | dict,
    toolkit: ToolKit,
    model,
    *,
    max_iterations: int = 6,
    as_of: str,
    review_id: str,
    term_text: str = "",
) -> AgentRun:
    payload = summary.model_dump() if isinstance(summary, ContractSummary) else dict(summary)
    clause = payload.get("clause_text") or payload.get("liability_cap") or payload.get("term") or ""
    counterparty = payload.get("counterparty", "")
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"counterparty: {counterparty}\n"
                f"review_id: {review_id}\n"
                f"as_of: {as_of}\n"
                f"clause: {clause}\n"
                f"term: {term_text or payload.get('term', '')}"
            ),
        },
    ]
    observations: list[str] = []
    memo_path = None
    content = ""
    used = 0
    for used in range(1, max_iterations + 1):
        turn: ModelTurn = model(messages)
        messages.append({"role": "assistant", "content": turn.content, "tool_calls": turn.tool_calls})
        content = turn.content
        if not turn.tool_calls:
            break
        for call in turn.tool_calls:
            name = call["name"]
            args = dict(call.get("args") or {})
            if name == "clause_risk_calculator":
                args.setdefault("clause_text", clause)
            elif name == "renewal_date_calendar":
                args.setdefault("as_of", as_of)
                args.setdefault("term_text", term_text or payload.get("term", "") or clause)
            elif name == "summary_memo_writer":
                args.setdefault("review_id", review_id)
                args.setdefault("counterparty", counterparty)
                args.setdefault("clause_text", clause)
                args.setdefault("as_of", as_of)
                args.setdefault("term_text", term_text or payload.get("term", "") or clause)
            observation = toolkit.invoke(name, args)
            observations.append(observation)
            if name == "summary_memo_writer" and observation.startswith("{"):
                import json

                memo_path = json.loads(observation).get("path")
            messages.append({"role": "tool", "tool_call_id": call.get("id", name), "content": observation})
    return AgentRun(content=content, observations=observations, iterations=used, memo_path=memo_path)
