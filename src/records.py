"""Review records addressed by id.

A review loads one playbook section, one counterparty, one contract, and one
e-signature envelope. The playbook section carries the preferred position, the
fallback, the walk-away, and the numeric thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass

from catalog import (
    ContractRecord,
    Counterparty,
    PlaybookDoc,
    SignatureRequest,
    load_contracts,
    load_counterparties,
    load_playbook,
    load_signature_requests,
)
from ai.playbook import chunk_markdown


class RecordNotFound(KeyError):
    """No row for that id in the LexOps tables."""


@dataclass(frozen=True)
class PlaybookSection:
    section_id: str
    title: str
    preferred: str
    fallback: str
    walk_away: str
    thresholds: str
    chunk_ids: tuple[str, ...]

    def positions(self) -> dict[str, str]:
        return {"preferred": self.preferred, "fallback": self.fallback, "walk_away": self.walk_away}


def _docs() -> dict[str, PlaybookDoc]:
    return {doc.slug: doc for doc in load_playbook()}


def _join(chunks, position: str) -> str:
    parts = [chunk.text.strip() for chunk in chunks if chunk.position == position and chunk.text.strip()]
    return "\n\n".join(parts)


def load_playbook_section(section_id: str) -> PlaybookSection:
    doc = _docs().get(section_id)
    if doc is None:
        raise RecordNotFound(section_id)
    chunks = chunk_markdown(doc.slug, doc.read_markdown())
    thresholds = [
        chunk.text.strip()
        for chunk in chunks
        if chunk.position is None and "threshold" in chunk.text.splitlines()[0].lower()
    ]
    return PlaybookSection(
        section_id=doc.slug,
        title=doc.title,
        preferred=_join(chunks, "preferred"),
        fallback=_join(chunks, "fallback"),
        walk_away=_join(chunks, "walk_away"),
        thresholds="\n\n".join(thresholds),
        chunk_ids=tuple(chunk.chunk_id for chunk in chunks),
    )


def load_counterparty(counterparty_id: str) -> Counterparty:
    for row in load_counterparties():
        if row.counterparty_id == counterparty_id:
            return row
    raise RecordNotFound(counterparty_id)


def load_contract(contract_id: str) -> ContractRecord:
    for row in load_contracts():
        if row.contract_id == contract_id:
            return row
    raise RecordNotFound(contract_id)


def load_envelope(envelope_id: str) -> SignatureRequest:
    for row in load_signature_requests():
        if row.envelope_id == envelope_id:
            return row
    raise RecordNotFound(envelope_id)


@dataclass(frozen=True)
class ReviewRecords:
    playbook: PlaybookSection
    counterparty: Counterparty
    contract: ContractRecord
    envelope: SignatureRequest


def load_review_records(
    *,
    section_id: str,
    counterparty_id: str,
    contract_id: str,
    envelope_id: str,
) -> ReviewRecords:
    """The four records one review reads before it compares a clause."""
    return ReviewRecords(
        playbook=load_playbook_section(section_id),
        counterparty=load_counterparty(counterparty_id),
        contract=load_contract(contract_id),
        envelope=load_envelope(envelope_id),
    )
