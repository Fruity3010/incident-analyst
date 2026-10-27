import json
import logging
from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app import llm
from app.agent import graph
from app.core.config import DEMO_USER
from app.llm import ProviderError
from app.schemas import ChatRequest

log = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["chat"])


def _sse(events: Iterator[dict]) -> Iterator[str]:
    try:
        for event in events:
            yield f"data: {json.dumps(event, default=str)}\n\n"
    except ProviderError as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    except Exception:
        log.exception("Agent run failed")
        yield f"data: {json.dumps({'type': 'error', 'message': 'The agent failed to answer. Please try again.'})}\n\n"


@router.post("/chat")
def chat(req: ChatRequest):
    llm.get_provider()
    events = graph.stream_answer(graph.get_agent(), req.message, req.thread_id, DEMO_USER)
    return StreamingResponse(_sse(events), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/chat/{thread_id}")
def chat_history(thread_id: str):
    return graph.get_history(graph.get_agent(), thread_id, DEMO_USER)
