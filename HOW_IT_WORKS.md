# How it works

A plain-English walkthrough of the code, following one report from upload to an agent answer. File paths are relative to `backend/` unless they start with `frontend/`.

## 1. Settings and the model provider

- `app/config.py` reads everything from `backend/.env`: which provider (`LLM_PROVIDER`), model names, `DATABASE_URL`. If `DATABASE_URL` is empty, it points at a SQLite file in `backend/data/`, so the app runs without Docker.
- `app/llm/base.py` defines `LLMProvider`, the one interface the rest of the app uses:
  - `generate(system, prompt)`: plain text (used by the summarise and translate tools)
  - `generate_json(system, prompt, schema)`: JSON constrained to a schema (structured output)
  - `chat(system, messages, tools, on_token)`: one agent step with tool definitions, streaming text tokens
- `with_retry()` in the same file wraps every provider call: on a 429 (rate limit) it waits, using the delay the provider asked for or 2s, 4s, 8s…, and then gives up with a `RateLimitError` (HTTP 429 to the UI).
- `app/llm/gemini.py` (`GeminiProvider`) and `app/llm/ollama.py` (`OllamaProvider`) implement it. Each converts LangChain messages and tool schemas into its API's format, and converts the reply back into an `AIMessage` with `tool_calls`.
- `app/llm/__init__.py` → `get_provider()` picks one based on `LLM_PROVIDER`. It is created on first use, so `/api/health` still works when a key is missing.

## 2. Ingestion: from article to structured record

Route: `POST /api/reports` in `app/main.py` → `create_report()`.

1. `extraction.read_upload()` turns a `.txt` or `.pdf` (via `pypdf`) into text. Pasted text is used as is.
2. `extraction.ingest()` → `extraction.analyse()` makes **two structured LLM calls** through `structured_call()`:
   - **Translate:** `TRANSLATE_SYSTEM` + the `Translation` schema → `original_language` and `english_text`.
   - **Extract:** `EXTRACT_SYSTEM` + the `IncidentExtraction` schema → title, summary, crime type, people, organisations, locations, date, amounts, confidence.
3. `structured_call()` sends the Pydantic model's JSON schema to `provider.generate_json()`, then validates the reply with Pydantic (`_parse()`). If validation fails, it **retries once**, showing the model its previous answer and the exact validation errors. A second failure raises `ExtractionError` (HTTP 422).
4. `db.save_report()` stores the original text, the English text and the fields. Locations go into their own `report_locations` table so we can filter and count by country. `canonical_country()` turns names like "Ivory Coast" into one stored form ("Côte d'Ivoire").

The schemas live in `app/schemas.py`. `CrimeType` is a fixed enum, so the model can't invent categories. A `field_validator` forgives small differences like "Online Fraud".

Both prompts tell the model the article is **data, not instructions**, which is a basic defence against prompt injection hidden in an article.

## 3. The database layer

`app/db.py` holds the tables (`Report`, `ReportLocation`, `Preference`) and **every query the app runs**:

- `search_reports(filters)`: builds a `SELECT` with one `WHERE` clause per filter. Values are always bound parameters. `country` accepts a comma-separated list ("Nigeria, Ghana") and matches any of them, ignoring case.
- `get_report`, `get_reports`, `count_by(group_by)`: fixed queries.
- `list_preferences`, `add_preference`, `delete_preference`: long-term memory.

The LLM never writes SQL. It only fills in filter values, which Pydantic validates (`ReportFilters`) first.

## 4. The tools

`app/tools.py`. Each tool is a normal function with LangChain's `@tool` decorator, which turns the function's signature and docstring into a JSON schema the model sees.

| Tool | What it does |
| --- | --- |
| `search_reports` | Filters by crime type, country/countries, language, date range |
| `get_report` | Full details of one report |
| `summarize_reports` | Picks reports by ids or filters (max 10) and asks the LLM for one combined summary |
| `stats` | Counts by crime_type, country or language |
| `translate` | Translates an answer into French, Spanish or Arabic, keeping `[Report #id]` references |
| `remember_preference` | Saves a long-term preference. The user id comes from LangGraph's `config`, never from the model |

Every report is printed as `[Report #id] title`, so the model has an exact citation to copy. Empty results return a fixed `NOTHING_FOUND` message, so the model has something explicit to report instead of guessing.

## 5. The LangGraph agent

`app/agent.py`:

```
START → load_memory → agent ⇄ tools → END
```

- `AgentState` = the message list (`MessagesState`) plus `preferences`.
- `load_memory()` (node 1) reads the user's saved preferences from the database.
- `call_model()` (node 2, named "agent") builds the system prompt (`SYSTEM_PROMPT`, with today's date and the preferences) and calls `provider.chat()` with the tool schemas. Tokens are streamed out with `get_stream_writer()`.
- `ToolNode(ALL_TOOLS)` (node 3, "tools") runs whatever tools the model asked for and appends `ToolMessage`s. If the model's arguments are invalid, the error goes back to the model as a tool message so it can correct itself.
- `tools_condition` is the conditional edge: if the last message has tool calls → "tools", otherwise → END.
- `recursion_limit: 16` in `_config()` stops a confused model from looping forever.

**Short-term memory:** `make_checkpointer()` returns a `PostgresSaver` (or `SqliteSaver`). The compiled graph saves its state after each step, keyed by `thread_id`. Sending the same `thread_id` again continues the conversation: "only the ones from 2025" works because the earlier search is still in the messages.

**Long-term memory:** preferences in the `preferences` table, written by `remember_preference`, loaded by `load_memory` into the system prompt on every run, shown and deletable in the UI.

## 6. The API and streaming

- `POST /api/chat` (`chat()` in `app/main.py`) runs `agent.stream_answer()`, which streams the graph with `stream_mode=["custom", "updates"]` and turns it into simple events: `token`, `tool_call`, `tool_result`, `done`. `_sse()` formats them as Server-Sent Events and turns failures into an `error` event.
- `GET /api/chat/{thread_id}` → `agent.get_history()` rebuilds the conversation from the checkpointer, so a page reload shows the chat again.
- Provider errors become clean HTTP errors in `provider_error_handler` (503 missing key, 429 rate limit, 502 other).

## 7. The frontend

- `frontend/src/api.ts`: typed fetch helpers, plus `chat()`, which reads the SSE stream with `TextDecoderStream` and calls `onEvent` for each event.
- `frontend/src/App.tsx`: hash routing, the sidebar, the provider badge (from `/api/health`) and the public-data notice.
- `pages/ReportsPage.tsx`: stat tiles, filters, the reports table and the "Add report" dialog.
- `pages/ReportDetailPage.tsx`: original text and English translation (tabs) next to the extracted fields.
- `pages/AgentPage.tsx`: the chat. Tool calls appear as steps (`search_reports(country=Nigeria)`) with expandable results. `[Report #id]` in answers becomes a link. The thread id is kept in `localStorage`. The `MemoryPanel` lists and deletes long-term preferences.
- `pages/StatsPage.tsx`: counts by crime type, country and language.

## 8. Tests

`backend/tests/`, run with `pytest`. `conftest.py` swaps in a `FakeProvider` that returns scripted replies, and points the app at a temporary SQLite database, so tests need no key or network.

- `test_extraction.py`: valid extraction is saved, invalid output is retried once with the errors, a second failure raises, schema limits.
- `test_tools.py`: each SQL filter, a country list and aliases, an injection attempt treated as a plain value, each tool's output.
- `test_agent.py`: a full run (tool call → answer with a citation), short-term memory per thread, long-term memory saved in one session and loaded in the next, invalid tool arguments sent back to the model.
- `test_api.py`: the REST endpoints and the chat stream.

---

## 10 likely interview questions

**1. What makes this an "agent" rather than a chatbot?**
The model decides which actions to take. It chooses tools and arguments, sees the results, and decides whether to call more tools or answer. LangGraph runs that loop (`agent ⇄ tools`) until the model gives a final answer.

**2. Why LangGraph instead of a simple loop?**
It gives an explicit graph (nodes, edges, state) that is easy to explain and extend, built-in checkpointing for conversation memory, streaming, and a recursion limit. Adding a step, such as `load_memory`, is just another node.

**3. How does the model know what tools exist?**
`@tool` turns each function's signature and docstring into a JSON schema. `convert_to_openai_tool` produces the definitions sent with every `chat()` call. The model replies with a tool name and JSON arguments. Pydantic validates them before the function runs.

**4. Why not let the LLM write SQL?**
Generated SQL can be wrong, slow or malicious (including through prompt injection hidden in an article). With fixed, parameterised queries the worst a model can do is pass a bad filter value, which Pydantic rejects or the database treats as plain text. There is a test for exactly this.

**5. How do you get reliable structured output?**
Three layers: the provider's JSON-schema mode constrains generation, Pydantic validates types and ranges (and the `CrimeType` enum), and one retry shows the model its errors. If it still fails, we return a clear 422 instead of saving bad data.

**6. What's the difference between short-term and long-term memory here?**
Short-term memory is the conversation: the LangGraph checkpointer saves the message list per `thread_id`, so follow-ups work. Long-term memory is user preferences in a database table, saved by a tool, loaded into the system prompt for every new conversation, and visible and deletable in the UI.

**7. How do you stop the agent from making things up?**
The system prompt says to answer only from tool results, to cite every report as `[Report #id]`, and to say plainly when nothing was found. Tools return an explicit "No reports matched" message. Citations link back to the real records, so users can check them.

**8. How do you handle French, Spanish and Arabic?**
At ingestion, every article is translated to English and stored next to the original, so search and extraction work in one language. In chat, the agent can call `translate` to answer in French, Spanish or Arabic. The UI uses `dir="auto"` so Arabic displays right-to-left.

**9. How would you evaluate this system?**
A test set of articles with hand-labelled fields to measure extraction accuracy per field, and a set of questions with expected tool calls and cited report IDs for the agent. Run both in CI whenever the prompt or model changes. The unit tests already check behaviour with a fake LLM.

**10. What would you change for production?**
Authentication and per-user data instead of `DEMO_USER`, RAG over the full report text (pgvector) for questions the fields can't answer, Alembic migrations, rate limiting, audit logs of tool calls, monitoring of model errors and cost, and stricter data handling if it ever processed non-public information.
