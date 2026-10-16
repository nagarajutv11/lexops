# LexOps data

Two trees live here. The toolkit export is checked in. CUAD contracts are downloaded locally and gitignored.

## `lexops/` — toolkit export

Synthetic Northwind playbook, intake queue, mock tables, and a 20-case golden set. See `lexops/manifest.json` and `lexops/README.md`.

The playbook is generated internal policy (preferred / fallback / walk-away, numeric thresholds, paraphrased examples). It does not copy CUAD contract text.

Intake request messages are synthetic. Each record's `attached_clause_text` is a clause span pasted from CUAD v1 (`clause_source` names the contract and category). The toolkit's original sentence is kept as `generated_clause_text`. The playbook does not copy CUAD text.

## `cuad/` — CUAD v1

**Licence: CC BY 4.0.**

Contract Understanding Atticus Dataset (CUAD) v1, The Atticus Project.

- Site: https://www.atticusprojectai.org/cuad
- Archive: https://zenodo.org/records/4595826
- DOI: https://doi.org/10.5281/zenodo.4595826
- Hugging Face mirror: https://huggingface.co/datasets/theatticusproject/cuad

Attribution: “Contract Understanding Atticus Dataset (CUAD) v1” by The Atticus Project, licensed under CC BY 4.0.

The Zenodo zip (about 106 MB) contains the master-clauses CSV, the SQuAD-style JSON, contract PDFs, and contract TXT files.

```text
py -3 scripts/download_cuad.py
```

Downloaded zip contents stay out of git. This licence note stays in the repo.
