"""Extract pipeline from Day 1 Session 1: raw JSON, Pydantic, repair loop.

Each review owns one message list. A repair turn is appended to that list.
Reviews do not share history.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import ValidationError

from ai.llm import ModelUnavailable, complete as default_complete
from ai.summary import FAMILIES, ContractSummary
from constants import SHORT_DISCLAIMER

Completer = Callable[[list[dict]], str]
StepNote = Callable[[str, str], None]

FIELD_LABELS = (
    ("term", "Term"),
    ("termination", "Termination"),
    ("liability_cap", "Liability cap"),
    ("indemnification", "Indemnification"),
    ("governing_law", "Governing law"),
    ("counterparty", "Counterparty"),
    ("agreement_type", "Agreement type"),
    ("raw_source_id", "Source id"),
)

EXTRACT_PROMPT = [
    {
        "role": "system",
        "content": (
            "You extract five clause families from a contract and nothing else: "
            "term, termination, liability_cap, indemnification, governing_law. "
            "Quote each family as a verbatim span from the contract. "
            "If a family is absent, set that field to exactly \"not stated\" and omit its clause. "
            "Copy counterparty, agreement_type, and raw_source_id exactly as given. "
            "Return one JSON object and no other text. "
            "Do not say whether a clause is enforceable or unenforceable. "
            "Do not give legal advice and do not say anyone should sign."
        ),
    },
    {
        "role": "user",
        "content": (
            "counterparty: {counterparty}\n"
            "agreement_type: {agreement_type}\n"
            "raw_source_id: {raw_source_id}\n\n"
            "Return JSON with keys term, termination, liability_cap, indemnification, "
            "governing_law, counterparty, agreement_type, raw_source_id, and clauses. "
            "Each clause has category, text, location, and an optional span "
            "(line, start, end). The clause text must equal the field for that category.\n\n"
            "CONTRACT:\n{contract_text}"
        ),
    },
]

REPAIR_PROMPT = [
    {
        "role": "user",
        "content": (
            "The previous JSON failed validation. Return one corrected JSON object and nothing else. "
            "Quote only text that appears in the contract. "
            "Use \"not stated\" when a family is absent. "
            "Do not add a legal conclusion.\n\n"
            "counterparty: {counterparty}\n"
            "agreement_type: {agreement_type}\n"
            "raw_source_id: {raw_source_id}\n\n"
            "CONTRACT:\n{contract_text}\n\n"
            "PREVIOUS JSON:\n{raw}\n\n"
            "VALIDATOR ERROR:\n{error}\n"
        ),
    },
]


@dataclass
class ExtractOutcome:
    summary: ContractSummary | None
    errors: list[dict]
    attempt_errors: list[str]
    raw_json: str
    disclaimer: str = SHORT_DISCLAIMER

    def panel(self) -> dict:
        """What the extraction panel renders: labeled fields, or field errors."""
        shared = {
            "extracted": True,
            "raw_json": self.raw_json,
            "disclaimer": self.disclaimer,
        }
        if self.summary is None:
            return {
                **shared,
                "extraction": [
                    {"field": item["field"], "value": "", "error": item["error"]} for item in self.errors
                ],
                "clauses": [],
                "errors": self.errors,
            }
        return {
            **shared,
            "extraction": [
                {"field": label, "value": getattr(self.summary, key), "error": None}
                for key, label in FIELD_LABELS
            ],
            "clauses": [clause.model_dump() for clause in self.summary.clauses],
            "errors": [],
            "summary": self.summary.model_dump(),
        }


def render_template(template: list[dict], **variables: str) -> list[dict]:
    """Day 1 Session 1 prompt template. Placeholders live in the template; contract text is a value."""
    return [{"role": message["role"], "content": message["content"].format(**variables)} for message in template]


def strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def field_errors(exc: ValidationError) -> list[dict]:
    rows = []
    for err in exc.errors():
        loc = [str(part) for part in err["loc"]]
        message = err["msg"]
        if message.startswith("Value error, "):
            message = message[len("Value error, ") :]
        field = ".".join(loc) if loc else "summary"
        if not loc and ": " in message:
            field, message = message.split(": ", 1)
        rows.append({"field": field, "error": message})
    return rows


def loads_object(raw: str) -> dict:
    data = json.loads(strip_fences(raw))
    if not isinstance(data, dict):
        raise json.JSONDecodeError("Expected a JSON object", raw, 0)
    return data


def extract_raw(text: str, *, meta: dict[str, str], history: list[dict], complete: Completer) -> str:
    """First turn on this review's message list."""
    history.extend(render_template(EXTRACT_PROMPT, contract_text=text, **meta))
    raw = complete(history)
    history.append({"role": "assistant", "content": raw or ""})
    return raw


def extract_repair(
    text: str,
    raw: str,
    error: Exception,
    *,
    meta: dict[str, str],
    history: list[dict],
    complete: Completer,
) -> str:
    """Append the original text, the bad output, and the validator error to this review."""
    history.extend(
        render_template(
            REPAIR_PROMPT,
            contract_text=text,
            raw=raw,
            error=str(error),
            **meta,
        )
    )
    repaired = complete(history)
    history.append({"role": "assistant", "content": repaired or ""})
    return repaired


def _note(on_step: StepNote | None, level: str, detail: str) -> None:
    if on_step is not None:
        on_step(level, detail)


def parse_contract(
    text: str,
    *,
    counterparty: str,
    agreement_type: str,
    raw_source_id: str,
    max_retries: int = 2,
    complete: Completer | None = None,
    on_step: StepNote | None = None,
) -> ExtractOutcome:
    """extract_raw → json.loads → ContractSummary. Validator errors go back to the model."""
    injected = complete

    def ask(messages: list[dict]) -> str:
        if injected is None:
            return default_complete(messages, json_mode=True, on_wait=on_step)
        return injected(messages)

    meta = {
        "counterparty": counterparty,
        "agreement_type": agreement_type,
        "raw_source_id": raw_source_id,
    }
    context = {"source": text, **meta}
    history: list[dict] = []
    errors: list[str] = []
    raw = ""
    _note(on_step, "info", "Asking the model to read the five clause families.")
    try:
        raw = extract_raw(text, meta=meta, history=history, complete=ask)
    except ModelUnavailable as exc:
        _note(on_step, "error", f"The model is unavailable. {exc}")
        return ExtractOutcome(None, [{"field": "model", "error": str(exc)}], errors, raw)
    _note(on_step, "info", "The model returned a response.")
    for attempt in range(max_retries + 1):
        if not raw or not str(raw).strip():
            caught: Exception = json.JSONDecodeError("Empty response", raw or "", 0)
        else:
            try:
                data = loads_object(raw)
                summary = ContractSummary.model_validate(data, context=context)
            except (json.JSONDecodeError, ValidationError) as exc:
                caught = exc
            else:
                _note(on_step, "info", "The response matched the five clause families.")
                return ExtractOutcome(summary, [], errors, raw)
        message = _error_text(caught)
        errors.append(message)
        _note(on_step, "error", f"The response failed validation. {message}")
        if attempt == max_retries:
            _note(on_step, "error", "No repairs left. Parse failed.")
            return ExtractOutcome(None, _final_errors(caught), errors, raw)
        _note(on_step, "info", "Asking the model to repair the response.")
        try:
            raw = extract_repair(text, raw, Exception(message), meta=meta, history=history, complete=ask)
        except ModelUnavailable as exc:
            _note(on_step, "error", f"The model is unavailable. {exc}")
            return ExtractOutcome(None, [{"field": "model", "error": str(exc)}], errors, raw)
        _note(on_step, "info", "The model returned a repaired response.")
    _note(on_step, "error", "Nothing was extracted.")
    return ExtractOutcome(None, [{"field": "json", "error": "Nothing was extracted."}], errors, raw)


def _error_text(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(f"{item['field']}: {item['error']}" for item in field_errors(exc))
    return str(exc)


def _final_errors(exc: Exception) -> list[dict]:
    if isinstance(exc, ValidationError):
        return field_errors(exc)
    return [{"field": "json", "error": "Response is not JSON. Nothing was extracted."}]


def families() -> tuple[str, ...]:
    return FAMILIES
