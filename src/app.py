"""HTTP API and page for deal review."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ai.llm import load_env, prepare_client
from ai.review import run_review
from ai.service import LexopsAI
from constants import DISCLAIMER, OUTPUTS_DIR, ROOT, SHORT_DISCLAIMER
from store import CONTRACT_TYPES, ApiError, Store

load_env()

WEB_DIR = ROOT / "web"


class DealIn(BaseModel):
    customer: str
    contract_type: str
    contract_text: str


class RoundIn(BaseModel):
    contract_text: str


class RedlineIn(BaseModel):
    redline_text: str
    liability_cap_redline: bool = False


class ReviewIn(BaseModel):
    counterparty: str
    clause_text: str
    request_text: str = ""
    agreement_type: str = "MSA"
    deadline_flag: bool | None = None


def default_store() -> Store:
    step = float(os.environ.get("LEXOPS_UI_STEP_SECONDS", "1.2"))
    db = Path(os.environ.get("LEXOPS_UI_DB", str(ROOT / ".lexops" / "ui.sqlite")))
    return Store(db, step_seconds=step, memo_dir=OUTPUTS_DIR)


def build_app(store: Store | None = None, complete=None) -> FastAPI:
    app = FastAPI(title="LexOps", docs_url=None, redoc_url=None)
    app.state.store = store or default_store()
    app.state.ai = LexopsAI(app.state.store, complete=complete)

    @app.exception_handler(ApiError)
    async def _api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/review")
    def review(body: ReviewIn) -> dict:
        decision = run_review(
            counterparty=body.counterparty,
            clause_text=body.clause_text,
            request_text=body.request_text,
            agreement_type=body.agreement_type,
            deadline_flag=body.deadline_flag,
        )
        return decision.model_dump()

    @app.get("/api/meta")
    def meta() -> dict:
        return {
            "short_disclaimer": SHORT_DISCLAIMER,
            "disclaimer": DISCLAIMER,
            "contract_types": list(CONTRACT_TYPES),
        }

    @app.get("/api/deals")
    def list_deals(status: str | None = None) -> dict:
        listed = app.state.store.list_deals(status)
        for deal in listed["deals"]:
            if deal["status"] == "in_review":
                app.state.ai.complete_review(deal["id"])
        return app.state.store.list_deals(status)

    @app.post("/api/deals")
    def create_deal(body: DealIn, background: BackgroundTasks) -> dict:
        deal = app.state.ai.create_deal(
            customer=body.customer,
            contract_type=body.contract_type,
            contract_text=body.contract_text,
        )
        background.add_task(app.state.ai.extract_saved_deal, deal["id"])
        return deal

    @app.get("/api/deals/{deal_id}")
    def get_deal(deal_id: int) -> dict:
        app.state.ai.complete_review(deal_id)
        return app.state.store.get_deal(deal_id)

    @app.post("/api/deals/{deal_id}/rounds")
    def add_round(deal_id: int, body: RoundIn) -> dict:
        return app.state.ai.add_round(deal_id, contract_text=body.contract_text)

    @app.post("/api/deals/{deal_id}/redline")
    def edit_redline(deal_id: int, body: RedlineIn) -> dict:
        return app.state.ai.edit_redline(
            deal_id,
            redline_text=body.redline_text,
            liability_cap_redline=body.liability_cap_redline,
        )

    @app.post("/api/deals/{deal_id}/approve")
    def approve(deal_id: int) -> dict:
        return app.state.ai.approve(deal_id)

    @app.post("/api/deals/{deal_id}/changes")
    def request_changes(deal_id: int) -> dict:
        return app.state.ai.request_changes(deal_id)

    @app.post("/api/deals/{deal_id}/reject")
    def reject(deal_id: int) -> dict:
        return app.state.ai.reject(deal_id)

    @app.post("/api/deals/{deal_id}/ceo-signoff")
    def ceo_signoff(deal_id: int) -> dict:
        return app.state.ai.ceo_signoff(deal_id)

    @app.get("/api/deals/{deal_id}/rounds/{round_id}/memo")
    def memo(deal_id: int, round_id: int) -> FileResponse:
        path = app.state.store.memo_file(deal_id, round_id)
        return FileResponse(path, media_type="text/markdown", filename=path.name)

    if WEB_DIR.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app


app = build_app()


def _index_playbook() -> None:
    """Fill pending playbook chunks without holding the HTTP server."""
    import logging

    log = logging.getLogger("lexops.app")
    log.info("Playbook RAG check started in the background.")
    try:
        from ai.playbook import LexOpsPlaybook

        LexOpsPlaybook().ensure_index()
    except Exception as exc:
        log.error("Playbook RAG check failed. The server stays up. %s", exc)


def main() -> None:
    import logging
    import threading

    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )
    log = logging.getLogger("lexops.app")
    log.info("Loading the model client before the server accepts requests.")
    if prepare_client():
        log.info("Model client ready.")
    else:
        log.error("LiteLLM is not installed. Deal extraction will fail until it is.")
    log.info("Starting server at http://127.0.0.1:8000")
    threading.Thread(target=_index_playbook, name="lexops-rag", daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
