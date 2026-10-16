"""Replace intake clause bodies with CUAD spans. Request wrappers stay synthetic.

The original toolkit sentence is kept on each row as generated_clause_text.
Playbook files are not touched.
"""

from __future__ import annotations

import ast
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "cuad" / "CUAD_v1" / "master_clauses.csv"
INTAKE_PATH = ROOT / "data" / "lexops" / "intake" / "records.jsonl"

# More specific phrases first. Values are CUAD category columns, in preference order.
RULES: list[tuple[tuple[str, ...], list[str]]] = [
    (("liquidated",), ["Liquidated Damages"]),
    (("uncapped", "super-cap", "carve-out"), ["Uncapped Liability", "Cap On Liability"]),
    (("indemnif",), ["Uncapped Liability", "Cap On Liability", "Covenant Not To Sue"]),
    (
        ("liability", "consequential", "limitation of remedy", "exclusive remedy"),
        ["Cap On Liability", "Uncapped Liability"],
    ),
    (
        ("governing law", "jurisdiction", "venue", "dispute", "arbitration"),
        ["Governing Law"],
    ),
    (("termination for convenience",), ["Termination For Convenience"]),
    (
        ("auto-renew", "automatic renewal", "renew"),
        ["Renewal Term", "Notice Period To Terminate Renewal"],
    ),
    (
        ("termination", "survival", "sunset"),
        ["Termination For Convenience", "Post-Termination Services", "Expiration Date"],
    ),
    (("audit",), ["Audit Rights"]),
    (("insurance",), ["Insurance"]),
    (
        ("non-solicit", "non-compete", "restricted covenant"),
        ["No-Solicit Of Employees", "Non-Compete", "No-Solicit Of Customers"],
    ),
    (("exclusiv", "territor"), ["Exclusivity"]),
    (("source code",), ["Source Code Escrow", "License Grant"]),
    (
        ("ip ownership", "ip assignment", "intellectual property", "work made", "background ip", "license", "trademark"),
        ["Ip Ownership Assignment", "License Grant", "Joint Ip Ownership"],
    ),
    (("assignment", "change of control"), ["Anti-Assignment", "Change Of Control"]),
    (
        ("most favored", "price", "pricing", "fee", "payment", "royalt", "billing"),
        ["Price Restrictions", "Revenue/Profit Sharing", "Minimum Commitment"],
    ),
    (("quota", "minimum commitment", "minimum sales"), ["Minimum Commitment", "Volume Restriction"]),
    (("warrant",), ["Warranty Duration"]),
    (("publicity", "non-disparag"), ["Non-Disparagement"]),
    (("confidential",), ["Non-Disparagement", "Post-Termination Services"]),
    (("data", "privacy", "hipaa", "scc", "security", "breach"), ["Audit Rights"]),
]

FALLBACK = {
    "escalation": ["Uncapped Liability", "Exclusivity", "Liquidated Damages", "Non-Compete", "Most Favored Nation"],
    "deviation": ["Termination For Convenience", "Ip Ownership Assignment", "Change Of Control", "Exclusivity"],
    "standard": ["Governing Law", "Cap On Liability", "Audit Rights", "Insurance", "Anti-Assignment", "Renewal Term"],
}


def load_spans() -> dict[str, list[tuple[str, str]]]:
    spans: dict[str, list[tuple[str, str]]] = defaultdict(list)
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            filename = row["Filename"]
            for category, raw in row.items():
                if category == "Filename" or "Answer" in category:
                    continue
                try:
                    value = ast.literal_eval(raw) if raw else []
                except (SyntaxError, ValueError):
                    continue
                if not isinstance(value, list):
                    continue
                for item in value:
                    text = " ".join(str(item).split())
                    if len(text) >= 40:
                        spans[category].append((filename, text))
    for category in spans:
        spans[category].sort(key=lambda pair: (pair[0], pair[1][:80]))
    return spans


def categories_for(truth: dict) -> list[str]:
    types = " ".join(truth.get("clause_types_present") or []).lower()
    band = truth.get("risk_band") or "standard"
    chosen: list[str] = []
    for phrases, categories in RULES:
        if any(phrase in types for phrase in phrases):
            chosen.extend(categories)
            break
    if not chosen:
        chosen = list(FALLBACK.get(band, FALLBACK["standard"]))
    if band == "escalation" and "Uncapped Liability" in chosen:
        chosen = ["Uncapped Liability", *[item for item in chosen if item != "Uncapped Liability"]]
    if band == "standard":
        mild = [item for item in chosen if item != "Uncapped Liability"]
        if mild:
            chosen = mild
    return chosen


def pick_span(spans: dict[str, list[tuple[str, str]]], categories: list[str], cursor: dict[str, int]) -> tuple[str, str, str]:
    for category in categories:
        pool = spans.get(category) or []
        preferred = [item for item in pool if 80 <= len(item[1]) <= 1600]
        use = preferred or pool
        if not use:
            continue
        index = cursor[category] % len(use)
        cursor[category] += 1
        filename, text = use[index]
        return category, filename, text
    raise RuntimeError(f"No CUAD span for {categories}")


def main() -> None:
    if not CSV_PATH.is_file():
        raise SystemExit(f"Missing {CSV_PATH}. Run scripts/download_cuad.py first.")
    spans = load_spans()
    cursor: dict[str, int] = defaultdict(int)
    used: dict[str, int] = defaultdict(int)
    rows = []
    for line in INTAKE_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))

    for record in rows:
        if "generated_clause_text" not in record:
            record["generated_clause_text"] = record.get("attached_clause_text") or ""
        if "generated_ground_truth" not in record:
            record["generated_ground_truth"] = record.get("ground_truth") or {}
        truth = dict(record["generated_ground_truth"])
        category, filename, text = pick_span(spans, categories_for(truth), cursor)
        record["attached_clause_text"] = text
        record["clause_source"] = {
            "dataset": "CUAD v1",
            "licence": "CC BY 4.0",
            "contract_filename": filename,
            "category": category,
        }
        truth["clause_types_present"] = [category]
        truth["deviations"] = []
        record["ground_truth"] = truth
        used[category] += 1

    INTAKE_PATH.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(f"updated {len(rows)} intake records")
    for category, count in sorted(used.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {count:3d}  {category}")


if __name__ == "__main__":
    main()
