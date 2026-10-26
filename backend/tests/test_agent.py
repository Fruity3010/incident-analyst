import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from app import agent, db
from tests.conftest import add_report


def call(name: str, **args) -> dict:
    return {"id": f"call_{name}", "name": name, "args": args}


@pytest.fixture
def graph():
    return agent.build_graph(InMemorySaver())


def test_full_run_calls_tool_streams_answer_and_cites(graph, fake):
    report_id = add_report("Ransomware hits Lagos hospital", "ransomware", country="Nigeria")
    fake.chat_replies = [
        AIMessage("", tool_calls=[call("search_reports", crime_type="ransomware", country="Nigeria")]),
        AIMessage(f"One match: [Report #{report_id}] Ransomware hits Lagos hospital."),
    ]

    events = list(agent.stream_answer(graph, "Any ransomware in Nigeria?", "t1", "demo"))
    types = [e["type"] for e in events]

    assert types[0] == "tool_call" and events[0]["args"] == {"crime_type": "ransomware", "country": "Nigeria"}
    assert types[1] == "tool_result" and f"[Report #{report_id}]" in events[1]["content"]
    assert "token" in types and types[-1] == "done"
    answer = "".join(e["text"] for e in events if e["type"] == "token")
    assert f"[Report #{report_id}]" in answer

    state = graph.get_state({"configurable": {"thread_id": "t1"}}).values
    assert [type(m) for m in state["messages"]] == [HumanMessage, AIMessage, ToolMessage, AIMessage]


def test_checkpointer_keeps_short_term_memory_per_thread(graph, fake):
    fake.chat_replies = [AIMessage("First answer."), AIMessage("Second answer."), AIMessage("Other thread.")]
    list(agent.stream_answer(graph, "ransomware reports?", "t1", "demo"))
    list(agent.stream_answer(graph, "only the ones from 2025", "t1", "demo"))
    list(agent.stream_answer(graph, "hello", "t2", "demo"))

    history = agent.get_history(graph, "t1", "demo")
    assert [t["content"] for t in history] == ["ransomware reports?", "First answer.", "only the ones from 2025", "Second answer."]
    assert len(agent.get_history(graph, "t2", "demo")) == 2


def test_long_term_memory_is_saved_by_tool_and_loaded_next_session(graph, fake):
    fake.chat_replies = [
        AIMessage("", tool_calls=[call("remember_preference", preference="Always answer in French")]),
        AIMessage("Noted."),
        AIMessage("Bonjour."),
    ]
    list(agent.stream_answer(graph, "Remember: always answer in French", "session-1", "alice"))
    with db.session() as s:
        assert [p.text for p in db.list_preferences(s, "alice")] == ["Always answer in French"]

    list(agent.stream_answer(graph, "hi", "session-2", "alice"))
    assert "- Always answer in French" in fake.chat_systems[-1]
    assert "(none saved)" in fake.chat_systems[0]


def test_invalid_tool_arguments_go_back_to_the_model(graph, fake):
    fake.chat_replies = [
        AIMessage("", tool_calls=[call("search_reports", crime_type="shoplifting")]),
        AIMessage("I could not search with that category."),
    ]
    events = list(agent.stream_answer(graph, "shoplifting?", "t1", "demo"))
    result = next(e for e in events if e["type"] == "tool_result")
    assert "error" in result["content"].lower()
    assert events[-1]["type"] == "done"
