"""Playbook risk score and renewal dates. The arithmetic stays in code.

The schedule is the Northwind methodology in `risk-scoring.md`: baseline 100,
deductions by clause family, and the low-risk band at 85 and above. A pasted
clause is scored from its own text. CUAD labels are not an input.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta

AUTO_FLOOR = 85.0
BASELINE = 100.0

_CATEGORY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("indemnification", re.compile(r"indemnif", re.IGNORECASE)),
    ("governing_law", re.compile(r"governing law|shall be governed|governed by|laws of", re.IGNORECASE)),
    ("sla_credits", re.compile(r"\bwarranty\b|uptime|service credit", re.IGNORECASE)),
    ("termination", re.compile(r"terminat|renewal|renew this", re.IGNORECASE)),
    ("liability_cap", re.compile(r"liabilit|consequential damage", re.IGNORECASE)),
    ("audit_rights", re.compile(r"\baudit\b|\binspect\b", re.IGNORECASE)),
    ("ip_ownership", re.compile(r"works made for hire|intellectual property|background ip|assigns to", re.IGNORECASE)),
    ("insurance", re.compile(r"\binsurance\b", re.IGNORECASE)),
    ("confidentiality", re.compile(r"confidential", re.IGNORECASE)),
    ("payment_terms", re.compile(r"\bpayment\b|\binvoice\b|\bprice\b|\brates\b|\bcpi\b", re.IGNORECASE)),
)

CATEGORY_SLUG = {
    "liability_cap": "clause-liability-cap",
    "indemnification": "clause-indemnification",
    "termination": "clause-termination",
    "governing_law": "clause-governing-law",
    "audit_rights": "clause-audit-rights",
    "ip_ownership": "clause-ip-ownership",
    "payment_terms": "clause-payment-terms",
    "insurance": "clause-insurance",
    "confidentiality": "clause-confidentiality",
    "sla_credits": "clause-sla-credits",
}

_APPROVED_LAW = re.compile(r"\b(delaware|new york|california)\b", re.IGNORECASE)
_MULTIPLIER = re.compile(r"(\d+(?:\.\d+)?)\s*x\b", re.IGNORECASE)
_WORD_TIMES = re.compile(r"\b(two|three|five|ten)\s+times\b", re.IGNORECASE)
_WORD_VALUE = {"two": 2.0, "three": 3.0, "five": 5.0, "ten": 10.0}
_NET_DAYS = re.compile(r"\bnet\s+(\d+)\b", re.IGNORECASE)
_MONTHS = re.compile(r"(\d+)\s*months?\b", re.IGNORECASE)
_YEARS = re.compile(r"(\d+)\s*years?\b", re.IGNORECASE)
_WAIVER_KEPT = (
    "shall not be liable",
    "neither party",
    "in no event",
    "exclusion of consequential",
    "not be liable for",
)


@dataclass(frozen=True)
class ClauseRisk:
    score: float
    band: str
    deductions: tuple[tuple[str, float], ...]
    in_playbook: bool
    auto_eligible: bool
    category: str | None
    walk_away: bool

    def as_dict(self) -> dict:
        data = asdict(self)
        data["deductions"] = [{"family": name, "points": points} for name, points in self.deductions]
        return data


def classify_clause(text: str) -> str | None:
    """Map a pasted clause to a playbook section, or None when LexOps has no section."""
    for name, pattern in _CATEGORY_PATTERNS:
        if pattern.search(text or ""):
            return name
    return None


def _multiplier(text: str) -> float | None:
    match = _MULTIPLIER.search(text)
    if match:
        return float(match.group(1))
    match = _WORD_TIMES.search(text)
    if match:
        return _WORD_VALUE[match.group(1).lower()]
    return None


def _uncapped(text: str) -> bool:
    lowered = text.lower()
    return "uncapped" in lowered or "unlimited liability" in lowered


def _liability_points(text: str) -> float:
    multiplier = _multiplier(text)
    if _uncapped(text) or (multiplier is not None and multiplier > 2):
        return 25.0
    lowered = text.lower()
    if "consequential" in lowered and not any(phrase in lowered for phrase in _WAIVER_KEPT):
        return 15.0
    return 0.0


def _indemnity_points(text: str) -> float:
    lowered = text.lower()
    if "indemnif" not in lowered:
        return 0.0
    if "without limitation" in lowered or "uncapped" in lowered or "unlimited" in lowered:
        return 15.0
    if "cap" in lowered or re.search(r"\d", text):
        return 0.0
    if "shall indemnify" in lowered or "fully indemnify" in lowered:
        return 15.0
    return 0.0


def _termination_points(text: str) -> float:
    lowered = text.lower()
    points = 0.0
    if "for convenience" in lowered or "without cause" in lowered:
        points = 10.0 if "penalty" in lowered or "without refund" in lowered else 7.0
    if "no cure" in lowered:
        points += 5.0
    return min(points, 10.0)


def _law_points(text: str) -> float:
    if not re.search(r"govern", text, re.IGNORECASE):
        return 0.0
    if _APPROVED_LAW.search(text):
        return 0.0
    return 3.0


def _ip_points(text: str) -> float:
    lowered = text.lower()
    if "background ip" in lowered or ("background" in lowered and "platform" in lowered):
        return 15.0
    if "works made for hire" in lowered or "exclusive property of the recipient" in lowered:
        return 7.0
    return 0.0


def _audit_points(text: str) -> float:
    lowered = text.lower()
    if "audit" not in lowered and "inspect" not in lowered:
        return 0.0
    if any(phrase in lowered for phrase in ("on-site", "on site", "employee record", "system access", "direct access")):
        return 10.0
    return 0.0


def _payment_points(text: str) -> float:
    lowered = text.lower()
    if "most favored" in lowered or "most favoured" in lowered or re.search(r"\bmfn\b", lowered):
        return 10.0
    match = _NET_DAYS.search(lowered)
    if match and int(match.group(1)) > 60:
        return 6.0
    return 0.0


def _confidentiality_points(text: str) -> float:
    lowered = text.lower()
    if "confidential" not in lowered:
        return 0.0
    if "perpetual" in lowered:
        return 5.0
    match = _YEARS.search(lowered)
    if match and int(match.group(1)) > 5:
        return 5.0
    return 0.0


def _walk_away(text: str) -> bool:
    multiplier = _multiplier(text)
    return _uncapped(text) or (multiplier is not None and multiplier >= 5)


def _band(score: float) -> str:
    if score >= AUTO_FLOOR:
        return "low"
    if score >= 71:
        return "medium"
    return "high"


def score_clause(text: str, *, category: str | None = None) -> ClauseRisk:
    """Deviation from the playbook thresholds. 100 is the standard paper."""
    chosen = category if category is not None else classify_clause(text)
    in_playbook = chosen is not None
    raw = {
        "liability_cap": min(25.0, _liability_points(text)),
        "indemnification": min(15.0, _indemnity_points(text)),
        "termination": _termination_points(text),
        "governing_law": min(5.0, _law_points(text)),
        "ip_ownership": min(15.0, _ip_points(text)),
        "audit_rights": min(10.0, _audit_points(text)),
        "payment_terms": min(10.0, _payment_points(text)),
        "confidentiality": min(10.0, _confidentiality_points(text)),
    }
    deductions = tuple((name, points) for name, points in raw.items() if points > 0)
    score = max(0.0, BASELINE - sum(points for _, points in deductions))
    walk = _walk_away(text)
    return ClauseRisk(
        score=score,
        band=_band(score),
        deductions=deductions,
        in_playbook=in_playbook,
        auto_eligible=in_playbook and score >= AUTO_FLOOR and not walk,
        category=chosen,
        walk_away=walk,
    )


def parse_term_months(text: str, default: int = 12) -> int:
    match = _MONTHS.search(text or "")
    if match:
        return int(match.group(1))
    match = _YEARS.search(text or "")
    if match:
        return int(match.group(1)) * 12
    return default


def add_months(day: date, months: int) -> date:
    index = day.month - 1 + months
    year = day.year + index // 12
    month = index % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def renewal_calendar(
    *,
    as_of: str,
    term_text: str = "",
    term_months: int | None = None,
    effective: str | None = None,
    notice_days: int = 30,
    auto_renew: bool = True,
) -> dict:
    """Next renewal and the notice window. Dates are computed, not guessed."""
    as_of_day = date.fromisoformat(as_of)
    months = term_months if term_months is not None else parse_term_months(term_text)
    start = date.fromisoformat(effective) if effective else as_of_day
    end = add_months(start, months)
    if end <= as_of_day and auto_renew:
        while end <= as_of_day:
            end = add_months(end, months)
    notice_opens = end - timedelta(days=notice_days)
    return {
        "term_months": months,
        "as_of": as_of_day.isoformat(),
        "effective": start.isoformat(),
        "next_renewal": end.isoformat(),
        "notice_days": notice_days,
        "notice_window_opens": notice_opens.isoformat(),
        "auto_renew": auto_renew,
    }
