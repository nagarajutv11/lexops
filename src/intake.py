"""Internal review requests. The deadline flag is stored and not a route input.

Aggressive terms and closing-day pressure are fields on the request. They are
read off the request text. Ground-truth labels stay in the evaluator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from catalog import IntakeRecord, load_intake

_DEADLINE = re.compile(
    r"clos(?:e|ing)\s+today|closing eod|just approve|stamped today",
    re.IGNORECASE,
)
_AGGRESSIVE = re.compile(
    r"\buncapped\b|\bwithout limitation\b|\bwon'?t budge\b|\bunlimited liability\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ReviewRequest:
    record_id: str
    counterparty: str
    agreement_type: str
    clause_text: str
    request_text: str
    contract_id: str | None
    aggressive_terms: bool
    deadline_pressure: bool
    deadline_flag: bool


def deadline_flag_for(request_text: str) -> bool:
    return bool(_DEADLINE.search(request_text or ""))


def aggressive_terms_for(*parts: str) -> bool:
    return bool(_AGGRESSIVE.search("\n".join(parts)))


def from_intake(row: IntakeRecord, *, contract_id: str | None = None) -> ReviewRequest:
    flag = deadline_flag_for(row.raw_text)
    return ReviewRequest(
        record_id=row.record_id,
        counterparty=row.counterparty_name,
        agreement_type=row.contract_type,
        clause_text=row.attached_clause_text,
        request_text=row.raw_text,
        contract_id=contract_id,
        aggressive_terms=aggressive_terms_for(row.raw_text, row.attached_clause_text),
        deadline_pressure=flag,
        deadline_flag=flag,
    )


def load_review_request(record_id: str) -> ReviewRequest:
    for row in load_intake():
        if row.record_id == record_id:
            return from_intake(row)
    raise KeyError(record_id)
