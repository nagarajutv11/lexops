# LexOps toolkit export

Generated corpus for the Northwind contract-review copilot. Counts are in `manifest.json`.

| Path | Contents |
|---|---|
| `corpus/index.json` | 19 documents: overview, risk methodology, disclaimer standard, 16 clause sections |
| `corpus/markdown/` and `corpus/pdf/` | Playbook text. Preferred / fallback / walk-away positions are paraphrased internal policy |
| `intake/records.jsonl` | 200 review requests. The message is synthetic. The attached clause is a CUAD v1 span (`clause_source`). `generated_clause_text` keeps the toolkit sentence |
| `mock_api/counterparties.*` | Counterparty history and posture |
| `mock_api/contracts.*` | Terms, renewal dates, risk scores |
| `mock_api/signature_requests.*` | E-signature envelopes |
| `eval/golden_set.json` | 20 eval cases (used in a later milestone) |

`manifest.json` records public datasets that informed the schema. Those sources were not copied into the playbook. CUAD itself is downloaded separately under `data/cuad/` and is licensed CC BY 4.0.

Playbook text, request messages, and mock tables are synthetic. Attached intake clauses are CUAD quotations. Treat `mock_api/` as the read-only source. Mutable review state belongs outside this folder.
