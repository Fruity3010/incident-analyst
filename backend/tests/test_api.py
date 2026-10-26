"""HTTP layer: report endpoints, the streamed chat, and memory delete."""

import json

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from app import agent, main
from tests.conftest import add_report
from tests.test_extraction import ARTICLE, TRANSLATION, VALID


def client(monkeypatch) -> TestClient:
    graph = agent.build_graph(InMemorySaver())
    monkeypatch.setattr(agent, "get_agent", lambda: graph)
    return TestClient(main.app)


def test_create_list_filter_and_read_reports(fake, monkeypatch):
    c = client(monkeypatch)
    fake.json_replies = [TRANSLATION, VALID]
    created = c.post("/api/reports", data={"text": ARTICLE})
    assert created.status_code == 201, created.text
    add_report("Ransomware hits Lagos hospital", country="Nigeria")

    assert len(c.get("/api/reports").json()) == 2
    senegal = c.get("/api/reports", params={"country": "Senegal"}).json()
    assert [r["title"] for r in senegal] == ["Online scam network dismantled in Dakar"]
    assert c.get("/api/reports", params={"crime_type": "not-a-type"}).status_code == 422
    assert c.get(f"/api/reports/{created.json()['id']}").json()["english_text"].startswith("Dakar")
    assert c.get("/api/reports/999").status_code == 404
    assert c.get("/api/stats").json()["country"][0]["count"] == 1


def test_chat_streams_events_and_memory_can_be_deleted(fake, monkeypatch):
    c = client(monkeypatch)
    fake.chat_replies = [
        AIMessage("", tool_calls=[{"id": "c1", "name": "remember_preference", "args": {"preference": "Answer in Spanish"}}]),
        AIMessage("Guardado."),
    ]
    with c.stream("POST", "/api/chat", json={"thread_id": "t1", "message": "Remember to answer in Spanish"}) as r:
        events = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    assert [e["type"] for e in events][:2] == ["tool_call", "tool_result"]
    assert events[-1]["type"] == "done"
    assert c.get("/api/chat/t1").json()[-1]["content"] == "Guardado."

    memory = c.get("/api/memory").json()
    assert [m["text"] for m in memory] == ["Answer in Spanish"]
    assert c.delete(f"/api/memory/{memory[0]['id']}").status_code == 204
    assert c.get("/api/memory").json() == []
