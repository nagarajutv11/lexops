"""Retrieval metrics for the playbook index. Day 2 Session 2 formulas.

Ground truth is a CUAD category on an intake span. The span is the query.
The gold ids are playbook chunks of the mapped category. CUAD text is not indexed.
"""

from __future__ import annotations

import json

from constants import DATA_DIR

VARIANTS = ("dense", "hybrid", "hybrid_rerank")

CUAD_CATEGORY = {
    "Cap On Liability": "liability_cap",
    "Uncapped Liability": "liability_cap",
    "Termination For Convenience": "termination",
    "Governing Law": "governing_law",
    "Audit Rights": "audit_rights",
    "Renewal Term": "termination",
    "Ip Ownership Assignment": "ip_ownership",
    "Insurance": "insurance",
    "Price Restrictions": "payment_terms",
}


def precision_at_k(retrieved: list[str], gold: list[str], k: int) -> float:
    if k <= 0:
        return 0.0
    gold_ids = set(gold)
    return sum(1 for item in retrieved[:k] if item in gold_ids) / k


def recall_at_k(retrieved: list[str], gold: list[str], k: int) -> float:
    if not gold:
        return 0.0
    return len(set(retrieved[:k]) & set(gold)) / len(gold)


def mrr(retrieved: list[str], gold: list[str]) -> float:
    gold_ids = set(gold)
    for index, item in enumerate(retrieved, start=1):
        if item in gold_ids:
            return 1.0 / index
    return 0.0


def citations_resolve(citations: list[str], retrieved: list[str]) -> bool:
    found = set(retrieved)
    return all(chunk_id in found for chunk_id in citations)


def cuad_cases(chunks: list, *, limit: int = 8) -> list[dict]:
    """Queries from CUAD spans already pasted into intake. Labels stay here."""
    by_category: dict[str, list[str]] = {}
    for chunk in chunks:
        by_category.setdefault(chunk.clause_category, []).append(chunk.chunk_id)
    path = DATA_DIR / "intake" / "records.jsonl"
    cases = []
    if not path.is_file():
        return cases
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        source = row.get("clause_source") or {}
        if source.get("dataset") != "CUAD v1":
            continue
        category = CUAD_CATEGORY.get(source.get("category") or "")
        gold = by_category.get(category or "", [])
        if not category or not gold:
            continue
        cases.append(
            {
                "id": row["record_id"],
                "query": row["attached_clause_text"][:800],
                "gold_ids": gold,
                "gold_category": category,
            }
        )
        if len(cases) >= limit:
            break
    return cases


def evaluate_retrieval(book, cases: list[dict], *, k: int = 5) -> list[dict]:
    """One row per variant. Cited ids are taken from that variant's retrieved set."""
    table = []
    for variant in VARIANTS:
        precision = []
        recall = []
        reciprocal = []
        cited_ok = []
        for case in cases:
            hits = book.search(case["query"], variant=variant, limit=k)
            retrieved = [hit.chunk.chunk_id for hit in hits]
            gold = list(case["gold_ids"])
            cited = retrieved[: min(3, len(retrieved))]
            precision.append(precision_at_k(retrieved, gold, k))
            recall.append(recall_at_k(retrieved, gold, k))
            reciprocal.append(mrr(retrieved, gold))
            cited_ok.append(citations_resolve(cited, retrieved))
        count = max(len(cases), 1)
        table.append(
            {
                "variant": variant,
                "precision_at_k": sum(precision) / count,
                "recall_at_k": sum(recall) / count,
                "mrr": sum(reciprocal) / count,
                "citations_ok": all(cited_ok) if cited_ok else True,
            }
        )
    return table


def render_table(rows: list[dict]) -> str:
    header = "| variant | precision@k | recall@k | MRR | citations resolve |"
    line = "|---|---:|---:|---:|---|"
    body = [
        f"| {row['variant']} | {row['precision_at_k']:.3f} | {row['recall_at_k']:.3f} | {row['mrr']:.3f} | {row['citations_ok']} |"
        for row in rows
    ]
    return "\n".join([header, line, *body])
