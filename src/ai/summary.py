"""ContractSummary: five clause families, quoted, never a legal conclusion."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

FAMILIES = ("term", "termination", "liability_cap", "indemnification", "governing_law")
NOT_STATED = "not stated"
BANNED_PHRASES = (
    "enforceable",
    "unenforceable",
    "you should sign",
    "authorized legal advice",
)

_JURISDICTION = re.compile(
    r"^(?:[Tt]he )?(?:[Ll]aws of )?(?:[Tt]he )?(?:[Ss]tate of )?[A-Z][A-Za-z .,'()/-]{0,70}$"
)
# A quoted clause may be the whole sentence. The jurisdiction still has to be named in it.
_LAW_OF = re.compile(
    r"\blaws of (?:the )?(?:state of )?[A-Za-z][A-Za-z.'-]{1,40}(?: [A-Za-z][A-Za-z.'-]{1,40})?",
    re.IGNORECASE,
)


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _banned(value: str) -> bool:
    lowered = value.lower()
    return any(phrase in lowered for phrase in BANNED_PHRASES)


_NUMBER_WORD = re.compile(
    r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"twenty|thirty|sixty|ninety)\b",
    re.IGNORECASE,
)


def _cap_ok(value: str) -> bool:
    if value.lower() == NOT_STATED:
        return True
    if len(value) > 240:
        return False
    if re.search(r"\d", value) or _NUMBER_WORD.search(value):
        return True
    lowered = value.lower()
    return "uncapped" in lowered or "unlimited" in lowered


class Span(BaseModel):
    """Optional pointer back into the source. Both offsets may be omitted."""

    model_config = ConfigDict(extra="ignore")

    line: int | None = None
    start: int | None = None
    end: int | None = None


class ClauseHit(BaseModel):
    """One quoted span for a single clause family."""

    model_config = ConfigDict(extra="ignore")

    category: str
    text: str
    location: str
    span: Span | None = None

    @field_validator("category")
    @classmethod
    def known_family(cls, value: str) -> str:
        category = value.strip()
        if category not in FAMILIES:
            raise ValueError(f"must be one of: {', '.join(FAMILIES)}")
        return category

    @field_validator("text", "location")
    @classmethod
    def required_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("required")
        if _banned(text):
            raise ValueError("remove legal-conclusion language")
        return text

    @field_validator("location")
    @classmethod
    def short_location(cls, value: str) -> str:
        if len(value) > 80:
            raise ValueError("location must be a short cite, such as a section heading")
        return value


class ContractSummary(BaseModel):
    """Validated extract. Missing JSON never becomes one of these."""

    model_config = ConfigDict(extra="ignore")

    term: str
    termination: str
    liability_cap: str
    indemnification: str
    governing_law: str
    counterparty: str
    agreement_type: str
    raw_source_id: str
    clauses: list[ClauseHit] = Field(default_factory=list)

    @field_validator("term", "termination", "indemnification", "counterparty", "agreement_type", "raw_source_id")
    @classmethod
    def required_field(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("required")
        if _banned(text):
            raise ValueError("remove legal-conclusion language")
        return text

    @field_validator("liability_cap")
    @classmethod
    def cap_shape(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("required")
        if _banned(text):
            raise ValueError("remove legal-conclusion language")
        if not _cap_ok(text):
            raise ValueError("must include a number, or say uncapped or not stated")
        return text

    @field_validator("governing_law")
    @classmethod
    def law_shape(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("required")
        if _banned(text):
            raise ValueError("remove legal-conclusion language")
        if text.lower() != NOT_STATED and not _JURISDICTION.match(text) and not _LAW_OF.search(text):
            raise ValueError("must be a jurisdiction name or not stated")
        return text

    @field_validator("agreement_type", "raw_source_id", "counterparty")
    @classmethod
    def short_metadata(cls, value: str) -> str:
        if len(value) > 120:
            raise ValueError("must be a short label")
        return value

    @model_validator(mode="after")
    def quotes_match_source(self, info: ValidationInfo) -> ContractSummary:
        context = info.context or {}
        source = context.get("source")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("summary: source text is required")
        expected = {
            "counterparty": context.get("counterparty"),
            "agreement_type": context.get("agreement_type"),
            "raw_source_id": context.get("raw_source_id"),
        }
        for field, wanted in expected.items():
            if wanted and getattr(self, field) != wanted:
                raise ValueError(f"{field}: must match the deal")
        families = [clause.category for clause in self.clauses]
        if len(families) != len(set(families)):
            raise ValueError("clauses: each category may appear once")
        by_category = {clause.category: clause for clause in self.clauses}
        normalized_source = _norm(source)
        lines = source.splitlines()
        for family in FAMILIES:
            value = getattr(self, family)
            hit = by_category.get(family)
            if value.lower() == NOT_STATED:
                if hit is not None:
                    raise ValueError(f"{family}: is not stated, so it cannot have a clause quote")
                continue
            if _norm(value) not in normalized_source:
                raise ValueError(f"{family}: is not a verbatim span of the contract")
            if hit is None:
                raise ValueError(f"{family}: needs a clause quote")
            if _norm(hit.text) != _norm(value):
                raise ValueError(f"{family}: does not match its clause quote")
            if _norm(hit.text) not in normalized_source:
                raise ValueError(f"{family}: clause quote is not in the contract")
            _check_span(hit, source, lines)
        return self


def _check_span(hit: ClauseHit, source: str, lines: list[str]) -> None:
    span = hit.span
    if span is None:
        return
    if span.start is not None or span.end is not None:
        if span.start is None or span.end is None:
            raise ValueError(f"{hit.category}: span needs both start and end")
        if span.start < 0 or span.end > len(source) or span.start >= span.end:
            raise ValueError(f"{hit.category}: span is outside the contract")
        if _norm(source[span.start : span.end]) != _norm(hit.text):
            raise ValueError(f"{hit.category}: span does not match the quoted text")
    if span.line is not None:
        if span.line < 1 or span.line > len(lines):
            raise ValueError(f"{hit.category}: line is outside the contract")
        if _norm(hit.text) not in _norm(lines[span.line - 1]):
            raise ValueError(f"{hit.category}: line does not contain the quoted text")
