# LexOps

Internal contract-review assistant for Northwind Systems. The page in `web/` is the product. It shows the disclaimer, a deal queue, and a review workspace. It is not legal advice.

Python 3.11 or newer. From the repository root.

## 1. Install

**Windows (PowerShell)**

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If activation is blocked by the execution policy, install with the venv interpreter directly:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copy `.env.template` to `.env` and set `GOOGLE_API_KEY` or `GEMINI_API_KEY` before using **Extract**. The deal list loads without that key.

## 2. Clean RAG

Deletes the Qdrant playbook collection and the `.embcache` files, then indexes the playbook from scratch.

**Windows (PowerShell)**

```powershell
.\.venv\Scripts\python.exe src\ai\playbook.py --reset
```

**macOS / Linux**

```bash
python src/ai/playbook.py --reset
```

## 3. Start server

**Windows (PowerShell)**

```powershell
.\.venv\Scripts\python.exe src\app.py
```

**macOS / Linux**

```bash
python src/app.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Stop the server with Ctrl+C.

If `.venv` is already activated, `python src/app.py` is enough. You do not need to recreate the virtual environment.

Reviews are stored in `.lexops/ui.sqlite`. Memos are written under `outputs/`. Both directories are gitignored.
