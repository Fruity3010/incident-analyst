import sqlite3
from collections.abc import Iterator
from datetime import date
from functools import lru_cache

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.utils.function_calling import convert_to_openai_tool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app import db, llm
from app.core import config
from app.agent.tools import ALL_TOOLS

TOOL_SCHEMAS = [convert_to_openai_tool(t) for t in ALL_TOOLS]

SYSTEM_PROMPT = """You are an assistant for analysts working with a database of PUBLIC news reports about crime and security incidents. Today is {today}.

Rules:
- Answer questions about reports ONLY with information from your tools. Do not use outside knowledge about incidents.
- Every time you mention a report, cite it as [Report #<id>] followed by its title.
- If the tools find nothing, say plainly that no matching reports were found. Never guess or invent reports.
- Follow-up questions build on the previous ones: keep earlier filters and add the new ones
  (e.g. "only the ones from 2025" means date_from=2025-01-01 and date_to=2025-12-31 on the same search).
- Countries are English names (e.g. "Nigeria"). For a region like "West Africa", list its countries in ONE search, comma-separated.
- If the user wants the answer in French, Spanish or Arabic, write the answer in English, pass it to the translate tool, and reply with the translation only.
- Use remember_preference only when the user asks you to remember something for future sessions.
- Be concise. Use short paragraphs or bullet points.

Long-term memory about this user (follow these preferences):
{preferences}"""


class AgentState(MessagesState):
    preferences: list[str]


def load_memory(state: AgentState, config: RunnableConfig) -> dict:
    with db.session() as s:
        prefs = db.list_preferences(s, config["configurable"]["user_id"])
    return {"preferences": [p.text for p in prefs]}


def call_model(state: AgentState) -> dict:
    writer = get_stream_writer()
    prefs = "\n".join(f"- {p}" for p in state.get("preferences", [])) or "(none saved)"
    system = SYSTEM_PROMPT.format(today=date.today().isoformat(), preferences=prefs)
    reply = llm.get_provider().chat(system, state["messages"], TOOL_SCHEMAS, on_token=lambda t: writer({"token": t}))
    return {"messages": [reply]}


def build_graph(checkpointer: BaseCheckpointSaver):
    graph = StateGraph(AgentState)
    graph.add_node("load_memory", load_memory)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(ALL_TOOLS))

    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpointer)


def make_checkpointer() -> BaseCheckpointSaver:
    if config.IS_POSTGRES:
        import psycopg
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg.rows import dict_row

        url = config.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
        conn = psycopg.connect(url, autocommit=True, prepare_threshold=0, row_factory=dict_row)
        saver = PostgresSaver(conn)
        saver.setup()
        return saver

    from langgraph.checkpoint.sqlite import SqliteSaver

    return SqliteSaver(sqlite3.connect(config.DATA_DIR / "checkpoints.db", check_same_thread=False))


@lru_cache
def get_agent():
    return build_graph(make_checkpointer())


def _config(thread_id: str, user_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id, "user_id": user_id}, "recursion_limit": 16}


def stream_answer(agent, message: str, thread_id: str, user_id: str) -> Iterator[dict]:
    inputs = {"messages": [HumanMessage(message)]}
    for mode, data in agent.stream(inputs, _config(thread_id, user_id), stream_mode=["custom", "updates"]):
        if mode == "custom":
            yield {"type": "token", "text": data["token"]}
            continue
        for node, update in data.items():
            if node == "agent":
                for tc in update["messages"][-1].tool_calls:
                    yield {"type": "tool_call", "id": tc["id"], "name": tc["name"], "args": tc["args"]}
            elif node == "tools":
                for m in update["messages"]:
                    yield {"type": "tool_result", "id": m.tool_call_id, "name": m.name, "content": m.content[:1500]}
    yield {"type": "done"}


def get_history(agent, thread_id: str, user_id: str) -> list[dict]:
    messages = agent.get_state(_config(thread_id, user_id)).values.get("messages", [])
    turns: list[dict] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            turns.append({"role": "user", "content": m.content, "tool_calls": []})
            continue
        if not turns or turns[-1]["role"] != "assistant":
            turns.append({"role": "assistant", "content": "", "tool_calls": []})
        turn = turns[-1]
        if isinstance(m, AIMessage):
            turn["content"] += m.content
            turn["tool_calls"] += [{"id": tc["id"], "name": tc["name"], "args": tc["args"]} for tc in m.tool_calls]
        elif isinstance(m, ToolMessage):
            for tc in turn["tool_calls"]:
                if tc["id"] == m.tool_call_id:
                    tc["result"] = m.content[:1500]
    return turns
