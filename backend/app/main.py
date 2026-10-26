"""FastAPI app: REST endpoints for reports, stats, memory, and the agent chat (streamed with SSE)."""

import json
import logging
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app import agent, config, db, extraction, llm
from app.llm import ProviderError
from app.schemas import CrimeType, Language, ReportDetail, ReportFilters, ReportOut

log = logging.getLogger("uvicorn.error")

# Single demo user. A real deployment would take this from the login session.
DEMO_USER = "demo"


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Incident Report Analyst Agent", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ProviderError)
def provider_error_handler(_: Request, e: ProviderError):
    """Missing key -> 503, rate limit -> 429, other provider errors -> 502."""
    return JSONResponse(status_code=e.status, content={"detail": str(e)})


@app.exception_handler(extraction.ExtractionError)
def extraction_error_handler(_: Request, e: extraction.ExtractionError):
    return JSONResponse(status_code=422, content={"detail": str(e)})


# ---------- health ----------


@app.get("/api/health")
def health():
    """Which provider/model is active. Never fails, so the UI can show config problems."""
    try:
        provider = llm.get_provider()
        return {"status": "ok", "provider": provider.name, "model": provider.chat_model, "database": "postgresql" if config.IS_POSTGRES else "sqlite"}
    except ProviderError as e:
        return {"status": "error", "provider": config.LLM_PROVIDER, "model": None, "error": str(e)}


# ---------- reports ----------


@app.post("/api/reports", response_model=ReportDetail, status_code=201)
async def create_report(text: str | None = Form(None), file: UploadFile | None = None):
    """Add a report from pasted text or an uploaded .txt/.pdf, then analyse and save it."""
    if file and file.filename:
        data = await file.read()
        if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(413, f"File is larger than {config.MAX_UPLOAD_MB} MB.")
        content, source = extraction.read_upload(file.filename, data), file.filename
    elif text and text.strip():
        content, source = text, None
    else:
        raise HTTPException(400, "Paste some text or upload a .txt/.pdf file.")
    # Blocking LLM calls: run in a worker thread so the server stays responsive
    from starlette.concurrency import run_in_threadpool

    return await run_in_threadpool(extraction.ingest, content, source)


@app.get("/api/reports", response_model=list[ReportOut])
def list_reports(
    crime_type: CrimeType | None = None,
    country: str | None = None,
    language: Language | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(200, le=500),
):
    filters = ReportFilters(crime_type=crime_type, country=country or None, language=language, date_from=date_from, date_to=date_to)
    with db.session() as s:
        return db.search_reports(s, filters, limit=limit)


@app.get("/api/reports/{report_id}", response_model=ReportDetail)
def read_report(report_id: int):
    with db.session() as s:
        report = db.get_report(s, report_id)
    if not report:
        raise HTTPException(404, "Report not found.")
    return report


@app.get("/api/stats")
def stats():
    with db.session() as s:
        return {
            group: [{"key": key, "count": n} for key, n in db.count_by(s, group)]
            for group in ("crime_type", "country", "language")
        }


# ---------- agent chat ----------


class ChatRequest(BaseModel):
    thread_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=4000)


def _sse(events: Iterator[dict]) -> Iterator[str]:
    """Format events as Server-Sent Events; turn errors into an error event."""
    try:
        for event in events:
            yield f"data: {json.dumps(event, default=str)}\n\n"
    except ProviderError as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    except Exception:
        log.exception("Agent run failed")
        yield f"data: {json.dumps({'type': 'error', 'message': 'The agent failed to answer. Please try again.'})}\n\n"


@app.post("/api/chat")
def chat(req: ChatRequest):
    """Stream the agent's answer: tool calls, tool results and answer tokens."""
    llm.get_provider()  # fail fast with a JSON error (e.g. missing key) before streaming starts
    events = agent.stream_answer(agent.get_agent(), req.message, req.thread_id, DEMO_USER)
    return StreamingResponse(_sse(events), media_type="text/event-stream")


@app.get("/api/chat/{thread_id}")
def chat_history(thread_id: str):
    """The saved conversation for a thread (from the LangGraph checkpointer)."""
    return agent.get_history(agent.get_agent(), thread_id, DEMO_USER)


# ---------- long-term memory ----------


@app.get("/api/memory")
def list_memory():
    with db.session() as s:
        return [{"id": p.id, "text": p.text, "created_at": p.created_at} for p in db.list_preferences(s, DEMO_USER)]


@app.delete("/api/memory/{pref_id}", status_code=204)
def delete_memory(pref_id: int):
    with db.session() as s:
        if not db.delete_preference(s, DEMO_USER, pref_id):
            raise HTTPException(404, "Preference not found.")
