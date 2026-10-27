# Incident Report Analyst Agent

A full-stack AI agent app for analysing public news reports about crime and security incidents, in **English, French, Spanish and Arabic**.

- **Ingest:** paste an article or upload a `.txt`/`.pdf`. The LLM detects the language, translates it to English and extracts a validated, structured record (crime type, people, organisations, locations, date, amounts, confidence). Everything is stored in PostgreSQL.
- **Ask the agent:** a **LangGraph** agent answers questions across all saved reports by choosing tools (search, get, summarise, stats, translate). It cites the reports it used and says so when it finds nothing.
- **Memory:** short-term conversation memory (a persisted LangGraph checkpointer, so follow-ups like *"only the ones from 2025"* work) and long-term per-user preferences (*"always answer in French"*) stored in the database.

> **Demo only.** This app is built for **public news articles**. Do not use it for real investigative, case or personal data. The 8 sample reports in `backend/scripts/seed.py` are **fictional**.

![Reports page](docs/screenshots/reports.png)

| Agent chat with visible tool calls | Report detail (original, translation, extracted fields) |
| --- | --- |
| ![Agent chat](docs/screenshots/agent.png) | ![Report detail](docs/screenshots/report.png) |

## Ingestion flow

```mermaid
flowchart LR
    A[Paste text or upload .txt / .pdf] --> B[read_upload<br/>pypdf for PDFs]
    B --> C["LLM call 1 (structured output)<br/>Translation: language + English text"]
    C --> D{Valid JSON?<br/>Pydantic}
    D -- no --> C2[Retry once with the<br/>validation errors] --> D2{Valid?}
    D2 -- no --> X[422 error]
    D -- yes --> E["LLM call 2 (structured output)<br/>IncidentExtraction"]
    D2 -- yes --> E
    E --> F{Valid?<br/>Pydantic, retry once}
    F -- yes --> G[(PostgreSQL<br/>reports + report_locations)]
    F -- no --> X
```

## Agent graph

```mermaid
flowchart LR
    S((START)) --> M[load_memory<br/>read long-term preferences]
    M --> A[agent<br/>LLM call with tool schemas]
    A -- tool calls --> T[tools<br/>ToolNode runs the tools]
    T --> A
    A -- final answer --> E((END))
    CP[(Checkpointer<br/>thread_id → messages)] -.saves state after every step.- A
```

**State** (`AgentState`): `messages` (the conversation, from LangGraph's `MessagesState`) plus `preferences` (loaded by `load_memory`).
**Tools:** `search_reports`, `get_report`, `summarize_reports`, `stats`, `translate`, `remember_preference`.
**Short-term memory:** the checkpointer (`PostgresSaver`, or `SqliteSaver` without Docker) stores the state per `thread_id`, so a conversation continues across requests and server restarts.
**Long-term memory:** the `preferences` table, written by the `remember_preference` tool and read by the `load_memory` node at the start of every run.

## Tech stack

| Layer | Tools |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, LangGraph, LangChain core |
| LLM | Google Gemini (default, `google-genai`) or Ollama (local), behind one provider interface, with retry and backoff on 429 |
| Database | PostgreSQL 16 via docker compose, or SQLite automatically when `DATABASE_URL` is empty |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4 |
| Tests | pytest with a fake LLM (no key or network needed) |

## Setup

You need Python 3.11+ and Node 20+.

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

**Option A: Gemini (default).** Get a free key at <https://aistudio.google.com/apikey> and set it in `backend/.env`:

```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key
GEMINI_CHAT_MODEL=gemini-3.5-flash-lite
```

**Option B: Ollama (fully local).** Install [Ollama](https://ollama.com), pull a model that supports tool calling, then set:

```bash
ollama pull llama3.2
```
```
LLM_PROVIDER=ollama
OLLAMA_CHAT_MODEL=llama3.2
```

### 2. Database

**Without Docker:** leave `DATABASE_URL` empty. The app uses SQLite files in `backend/data/`.

**With Docker (PostgreSQL):**

```bash
docker compose up -d          # from the repo root, Postgres on port 5433
```

and in `backend/.env`:

```
DATABASE_URL=postgresql+psycopg://analyst:analyst@localhost:5433/incidents
```

Tables are created on startup.

### 3. Seed and run

```bash
cd backend
python -m scripts.seed                 # 8 fictional demo reports, no LLM calls
uvicorn app.main:app --reload          # http://localhost:8000
```

```bash
cd frontend
npm install
npm run dev                            # http://localhost:5173, proxies /api to :8000
```

If the API runs on another port, start the frontend with `API_URL=http://localhost:8010 npm run dev`.

### Tests

```bash
cd backend
pytest
```

The tests use a fake LLM provider, so they run offline. They cover extraction validation and retry, each tool, the SQL filters (including an injection attempt), the API, and a full agent run with memory.

## API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | Active provider, model and database |
| POST | `/api/reports` | Add a report (form field `text`, or `file` .txt/.pdf); runs the analysis |
| GET | `/api/reports` | List reports. Filters: `crime_type`, `country` (comma-separated list allowed), `language`, `date_from`, `date_to` |
| GET | `/api/reports/{id}` | One report with original text, translation and all fields |
| GET | `/api/stats` | Counts by crime type, country and language |
| POST | `/api/chat` | `{thread_id, message}`; streams Server-Sent Events: `token`, `tool_call`, `tool_result`, `error`, `done` |
| GET | `/api/chat/{thread_id}` | Saved conversation for a thread (from the checkpointer) |
| GET | `/api/memory` | Long-term preferences |
| DELETE | `/api/memory/{id}` | Delete a preference |

Interactive docs: <http://localhost:8000/docs>.

## Design decisions

**Tools instead of letting the LLM write SQL.** Each tool calls a fixed, parameterised query in `app/db/queries.py`. The LLM only supplies filter *values*, which Pydantic validates (for example, `crime_type` must be one of the 9 allowed values) before they reach the database as bound parameters. This prevents SQL injection and prompt-injected queries, keeps the agent's abilities explicit and testable, and gives reviewers a readable trace of what it did.

**Structured outputs.** Both ingestion steps use the provider's JSON-schema mode (`response_json_schema` for Gemini, `format` for Ollama), generated from the Pydantic models. The output is still validated with Pydantic, because models can break a schema. On invalid output we retry once, showing the model its answer and the validation errors. The fixed `CrimeType` enum keeps categories consistent for filtering and stats.

**Two-step ingestion.** Translating first, then extracting from English, keeps the extraction prompt simple and gives analysts a translation to compare against the original side by side.

**Memory design.** Short-term memory is the LangGraph checkpointer: the full message list per `thread_id`, persisted in the same database, so follow-ups reuse earlier filters. Long-term memory is a plain `preferences` table, because preferences must outlive any single conversation, be visible in the UI and be deletable by the user. The `load_memory` node puts them into the system prompt at the start of every run.

**Provider abstraction.** `app/llm/base.py` defines one interface (`generate`, `generate_json`, `chat`) with Gemini and Ollama implementations, so the agent and ingestion code never depend on a vendor SDK. Retry with backoff honours Gemini's `retryDelay` on 429.

**Grounded answers.** Tools format every report as `[Report #id] title`, and the system prompt requires citing them and saying when nothing was found. The UI turns citations into links to the report.

**Countries.** A `country` filter accepts a comma-separated list, so a region like "West Africa" is one search, and common alternative names ("Ivory Coast" / "Côte d'Ivoire", "UK", "UAE") resolve to the same stored name.

## Limitations

- Search is by structured fields only; it does not search the article text itself.
- The country alias list is small and hand-written.
- One demo user (`DEMO_USER`), no authentication.
- Scanned PDFs (images without a text layer) are not supported.
- Small local models (e.g. llama3.2 3B) choose tools less reliably than Gemini.

## Future improvements

- **RAG over report text:** embed the English text (pgvector) and add a `semantic_search` tool for questions the fields can't answer.
- **Evaluation:** a fixed set of questions with expected tool calls and cited report IDs, run in CI to catch prompt or model regressions; extraction accuracy measured against hand-labelled articles.
- **Microsoft 365 Copilot connector:** expose the tools through a Copilot / Graph connector so analysts can query reports from Teams.
- Authentication and per-user data, entity resolution across reports (same person or group), a map view, and export to CSV/STIX.

## Project structure

```
backend/
  app/
    main.py              FastAPI app: CORS, error handlers, routers
    api/                 Routes: health, reports (+ stats), chat (SSE), memory
    core/config.py       Settings from backend/.env
    agent/graph.py       LangGraph graph, system prompt, checkpointer
    agent/tools.py       The agent's tools
    services/extraction.py  Translation + structured extraction with validation and retry
    db/models.py         SQLAlchemy tables
    db/queries.py        Every query the app runs (parameterised)
    db/session.py        Engine and sessions (PostgreSQL or SQLite)
    llm/                 Provider interface, Gemini and Ollama
    schemas.py           Pydantic models
  scripts/seed.py        8 fictional demo reports (EN/FR/ES/AR)
  tests/                 pytest, fake LLM
frontend/src/
  pages/                 Reports, Report detail, Agent chat (+ memory panel), Stats
  components/ui.tsx      Shared UI pieces
  api.ts                 Typed API client and SSE reader
docker-compose.yml       PostgreSQL 16
```

See [HOW_IT_WORKS.md](HOW_IT_WORKS.md) for a walkthrough of the code.
