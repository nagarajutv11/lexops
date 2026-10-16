"""Read-only access to the toolkit export under data/lexops and the CUAD drop."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from constants import CUAD_DIR, DATA_DIR


@dataclass(frozen=True)
class IntakeRecord:
    record_id: str
    request_id: str
    channel: str
    requester_role: str
    received_at: str
    raw_text: str
    counterparty_name: str
    contract_type: str
    annual_contract_value_usd: float | None
    attached_clause_text: str
    risk_band: str
    requires_human_review: bool

    @classmethod
    def from_obj(cls, obj: dict) -> IntakeRecord:
        raw = obj.get("raw_text") or ""
        truth = obj.get("ground_truth") or {}
        acv = obj.get("annual_contract_value_usd")
        return cls(
            record_id=obj["record_id"],
            request_id=obj.get("request_id") or "",
            channel=obj.get("channel") or "",
            requester_role=obj.get("requester_role") or "",
            received_at=obj.get("received_at") or "",
            raw_text=raw,
            counterparty_name=obj.get("counterparty_name") or "",
            contract_type=obj.get("contract_type") or "",
            annual_contract_value_usd=None if acv is None else float(acv),
            attached_clause_text=obj.get("attached_clause_text") or "",
            risk_band=truth.get("risk_band") or "",
            requires_human_review=bool(truth.get("requires_human_review")),
        )

    def label(self) -> str:
        return f"{self.record_id} · {self.counterparty_name} · {self.contract_type}"


@dataclass(frozen=True)
class PlaybookDoc:
    slug: str
    title: str
    section: str
    markdown_path: Path
    pdf_path: Path

    def read_markdown(self) -> str:
        return self.markdown_path.read_text(encoding="utf-8")


@dataclass(frozen=True)
class Counterparty:
    counterparty_id: str
    legal_name: str
    jurisdiction: str
    relationship: str
    negotiation_rounds_to_date: int
    historical_posture: str

    def label(self) -> str:
        return f"{self.counterparty_id} · {self.legal_name} · {self.historical_posture}"


@dataclass(frozen=True)
class ContractRecord:
    contract_id: str
    counterparty_id: str
    contract_type: str
    status: str
    effective_date: str
    term_months: int
    auto_renew: bool
    renewal_notice_days: int
    annual_value_usd: float
    liability_cap_multiple: float
    risk_score: int


@dataclass(frozen=True)
class SignatureRequest:
    envelope_id: str
    contract_id: str
    status: str
    sent_at: str
    signer_email: str


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_manifest() -> dict:
    return _read_json(DATA_DIR / "manifest.json")


@lru_cache(maxsize=1)
def load_intake() -> tuple[IntakeRecord, ...]:
    path = DATA_DIR / "intake" / "records.jsonl"
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(IntakeRecord.from_obj(json.loads(line)))
    return tuple(records)


@lru_cache(maxsize=1)
def load_playbook() -> tuple[PlaybookDoc, ...]:
    docs = []
    for item in _read_json(DATA_DIR / "corpus" / "index.json"):
        docs.append(
            PlaybookDoc(
                slug=item["slug"],
                title=item["title"],
                section=item["section"],
                markdown_path=DATA_DIR / item["markdown"],
                pdf_path=DATA_DIR / item["pdf"],
            )
        )
    return tuple(docs)


@lru_cache(maxsize=1)
def load_counterparties() -> tuple[Counterparty, ...]:
    rows = _read_json(DATA_DIR / "mock_api" / "counterparties.json")
    return tuple(
        Counterparty(
            counterparty_id=row["counterparty_id"],
            legal_name=row["legal_name"],
            jurisdiction=row["jurisdiction"],
            relationship=row["relationship"],
            negotiation_rounds_to_date=int(row["negotiation_rounds_to_date"]),
            historical_posture=row["historical_posture"],
        )
        for row in rows
    )


@lru_cache(maxsize=1)
def load_contracts() -> tuple[ContractRecord, ...]:
    rows = _read_json(DATA_DIR / "mock_api" / "contracts.json")
    return tuple(
        ContractRecord(
            contract_id=row["contract_id"],
            counterparty_id=row["counterparty_id"],
            contract_type=row["contract_type"],
            status=row["status"],
            effective_date=row["effective_date"],
            term_months=int(row["term_months"]),
            auto_renew=bool(row["auto_renew"]),
            renewal_notice_days=int(row["renewal_notice_days"]),
            annual_value_usd=float(row["annual_value_usd"]),
            liability_cap_multiple=float(row["liability_cap_multiple"]),
            risk_score=int(row["risk_score"]),
        )
        for row in rows
    )


@lru_cache(maxsize=1)
def load_signature_requests() -> tuple[SignatureRequest, ...]:
    rows = _read_json(DATA_DIR / "mock_api" / "signature_requests.json")
    return tuple(
        SignatureRequest(
            envelope_id=row["envelope_id"],
            contract_id=row["contract_id"],
            status=row["status"],
            sent_at=row["sent_at"],
            signer_email=row["signer_email"],
        )
        for row in rows
    )


def cuad_inventory() -> dict:
    """Locate CUAD v1 artifacts after scripts/download_cuad.py has run."""
    csvs = list(CUAD_DIR.rglob("master_clauses.csv"))
    jsons = [
        path
        for path in CUAD_DIR.rglob("*.json")
        if path.name.lower().endswith(".json") and "cuad" in path.name.lower()
    ]
    pdfs = [path for path in CUAD_DIR.rglob("*.pdf")]
    txts = [
        path
        for path in CUAD_DIR.rglob("*.txt")
        if "readme" not in path.name.lower() and "datasheet" not in path.name.lower()
    ]
    return {
        "ready": bool(csvs) and bool(jsons) and len(pdfs) > 0 and len(txts) > 0,
        "master_clauses": csvs[0] if csvs else None,
        "squad_json": jsons[0] if jsons else None,
        "pdf_count": len(pdfs),
        "txt_count": len(txts),
    }
