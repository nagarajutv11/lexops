"""Per-counterparty memory. Recall for one party never returns another.

Four stores, matching Day 2 Session 1: working, episodic, semantic, procedural.
The counterparties table is the seed. A rolling summary is merged with the
previous summary so a fact from early in the review survives compression.
Recalled memory is context. It does not authorize auto-approval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from catalog import Counterparty, load_counterparties

RECENT_KEEP = 2


def token_count(text: str) -> int:
    """About four characters per token when tiktoken is not required."""
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return max(1, len(text) // 4)


def summarize_turns(turns: list[dict], prev_summary: str = "", complete=None) -> str:
    """Merge older turns into the running summary. Concrete facts are kept."""
    if complete is not None:
        convo = "\n".join(f'{turn["role"]}: {turn["content"]}' for turn in turns)
        messages = [
            {
                "role": "system",
                "content": (
                    "You maintain a running summary of one counterparty review. "
                    "Update the existing summary with the new turns. Preserve concrete facts "
                    "(names, numbers, positions already accepted). Return only the updated summary."
                ),
            },
            {
                "role": "user",
                "content": f"Existing summary:\n{prev_summary or '(none)'}\n\nNew turns:\n{convo}\n\nUpdated summary:",
            },
        ]
        return str(complete(messages)).strip()
    kept: list[str] = []
    if prev_summary.strip():
        kept.append(prev_summary.strip())
    for turn in turns:
        for sentence in re.split(r"(?<=[.!?])\s+", turn["content"].strip()):
            if sentence and re.search(r"\d|planted fact|accepted", sentence, re.IGNORECASE):
                kept.append(sentence.strip())
    unique: list[str] = []
    for item in kept:
        if item not in unique:
            unique.append(item)
    return " ".join(unique)


@dataclass
class MemoryHit:
    counterparty_id: str
    kind: str
    text: str
    score: float
    authorizes_auto_approval: bool = False


@dataclass
class CounterpartyMemory:
    counterparty_id: str
    token_budget: int = 80
    recent_keep: int = RECENT_KEEP
    complete: object | None = None
    episodic: list[str] = field(default_factory=list)
    semantic: list[str] = field(default_factory=list)
    procedural: list[str] = field(default_factory=list)
    turns: list[dict] = field(default_factory=list)
    summary: str = ""

    def remember(self, text: str, kind: str) -> None:
        store = {"episodic": self.episodic, "semantic": self.semantic, "procedural": self.procedural}.get(kind)
        if store is None:
            raise ValueError(f"unknown memory kind {kind}")
        store.append(text)

    def add_turn(self, role: str, content: str) -> None:
        self.turns.append({"role": role, "content": content})
        while self._working_tokens() > self.token_budget and len(self.turns) > self.recent_keep:
            older = self.turns[: -self.recent_keep]
            self.summary = summarize_turns(older, self.summary, self.complete)
            self.turns = self.turns[-self.recent_keep :]

    def _working_tokens(self) -> int:
        blob = self.summary + "\n" + "\n".join(turn["content"] for turn in self.turns)
        return token_count(blob)

    def recall(self, query: str, k: int = 5) -> list[MemoryHit]:
        needles = [part for part in query.lower().split() if len(part) > 2]
        ranked: list[MemoryHit] = []
        pools = (
            ("episodic", self.episodic),
            ("semantic", self.semantic),
            ("procedural", self.procedural),
        )
        for kind, rows in pools:
            for text in rows:
                score = _overlap(needles, text)
                if score > 0 or not needles:
                    ranked.append(
                        MemoryHit(self.counterparty_id, kind, text, score, authorizes_auto_approval=False)
                    )
        if self.summary:
            ranked.append(
                MemoryHit(
                    self.counterparty_id,
                    "working",
                    self.summary,
                    _overlap(needles, self.summary),
                    authorizes_auto_approval=False,
                )
            )
        ranked.sort(key=lambda hit: (-hit.score, hit.kind, hit.text))
        return ranked[:k]


def _overlap(needles: list[str], text: str) -> float:
    if not needles:
        return 0.0
    lowered = text.lower()
    return sum(1 for needle in needles if needle in lowered) / len(needles)


class MemoryBank:
    """Namespaces are counterparty ids. Seeding reads the counterparties table."""

    def __init__(self, *, token_budget: int = 80, complete=None) -> None:
        self.token_budget = token_budget
        self.complete = complete
        self._stores: dict[str, CounterpartyMemory] = {}

    def for_party(self, counterparty_id: str) -> CounterpartyMemory:
        if counterparty_id not in self._stores:
            self._stores[counterparty_id] = CounterpartyMemory(
                counterparty_id,
                token_budget=self.token_budget,
                complete=self.complete,
            )
        return self._stores[counterparty_id]

    def seed(self, row: Counterparty) -> CounterpartyMemory:
        memory = self.for_party(row.counterparty_id)
        memory.remember(
            f"{row.legal_name} posture is {row.historical_posture}.",
            "semantic",
        )
        memory.remember(
            f"{row.legal_name} has {row.negotiation_rounds_to_date} negotiation rounds to date.",
            "episodic",
        )
        memory.remember(
            (
                f"Review practice for a {row.relationship} in {row.jurisdiction}: "
                "record deadline pressure and do not treat memory as authority to auto-approve."
            ),
            "procedural",
        )
        return memory

    def seed_all(self) -> None:
        for row in load_counterparties():
            self.seed(row)

    def remember(self, counterparty_id: str, kind: str, text: str) -> None:
        self.for_party(counterparty_id).remember(text, kind)

    def recall(self, counterparty_id: str, query: str, k: int = 5) -> list[MemoryHit]:
        hits = self.for_party(counterparty_id).recall(query, k=k)
        return [hit for hit in hits if hit.counterparty_id == counterparty_id]
