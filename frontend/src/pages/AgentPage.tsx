import { Fragment, useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { api, type ChatEvent, type ChatTurn, type Preference, type ToolCall } from "../api";
import { Card, ErrorBox, Icon, PageHeader, Spinner, errorMessage, primaryButton, secondaryButton } from "../components/ui";

const THREAD_KEY = "ira-thread-id";

const SUGGESTIONS = [
  { title: "Find reports", text: "Which ransomware or phishing reports do we have?" },
  { title: "Summarise a region", text: "Summarise the reports from West Africa" },
  { title: "Count", text: "Count reports by country" },
  { title: "Save a preference", text: "Remember that I focus on West Africa" },
];

const TOOLS = ["search_reports", "get_report", "summarize_reports", "stats", "translate", "remember_preference"];

function storedThreadId(): string {
  try {
    const saved = localStorage.getItem(THREAD_KEY);
    if (saved) return saved;
  } catch {}
  return freshThreadId();
}

function freshThreadId(): string {
  const id = crypto.randomUUID();
  try {
    localStorage.setItem(THREAD_KEY, id);
  } catch {}
  return id;
}

export default function AgentPage() {
  const [threadId, setThreadId] = useState(storedThreadId);
  const [turns, setTurns] = useState<ChatTurn[] | null>(null);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [memoryVersion, setMemoryVersion] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setTurns(null);
    api
      .history(threadId)
      .then(setTurns)
      .catch(() => setTurns([]));
  }, [threadId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [turns]);

  useEffect(() => () => abortRef.current?.abort(), []);

  async function ask(question: string) {
    if (!question.trim() || streaming) return;
    setInput("");
    setError(null);
    setStreaming(true);
    setTurns((prev) => [...(prev ?? []), { role: "user", content: question, tool_calls: [] }, { role: "assistant", content: "", tool_calls: [] }]);

    const updateLast = (fn: (t: ChatTurn) => ChatTurn) => setTurns((prev) => (prev ? [...prev.slice(0, -1), fn(prev[prev.length - 1])] : prev));

    function onEvent(e: ChatEvent) {
      if (e.type === "token") updateLast((t) => ({ ...t, content: t.content + e.text }));
      else if (e.type === "tool_call")
        updateLast((t) => ({ ...t, content: t.content ? t.content + "\n\n" : "", tool_calls: [...t.tool_calls, { id: e.id, name: e.name, args: e.args }] }));
      else if (e.type === "tool_result")
        updateLast((t) => ({ ...t, tool_calls: t.tool_calls.map((c) => (c.id === e.id ? { ...c, result: e.content } : c)) }));
      else if (e.type === "error") setError(e.message);
    }

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await api.chat(threadId, question, onEvent, controller.signal);
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError(errorMessage(e));
    } finally {
      setStreaming(false);
      abortRef.current = null;
      setMemoryVersion((v) => v + 1);
    }
  }

  function newChat() {
    abortRef.current?.abort();
    setError(null);
    setThreadId(freshThreadId());
  }

  return (
    <>
      <PageHeader
        title="Ask the agent"
        description="A LangGraph agent that answers questions across all saved reports by choosing tools. Every answer cites the reports it used."
        actions={
          <button type="button" className={secondaryButton} onClick={newChat} disabled={!turns?.length && !streaming}>
            <Icon name="plus" />
            New chat
          </button>
        }
      />
    <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
      <Card className="flex h-[calc(100dvh-14rem)] min-h-[30rem] flex-col">
        <div className="flex-1 space-y-6 overflow-y-auto px-5 py-6 sm:px-8">
          {turns === null ? (
            <Spinner label="Loading conversation…" />
          ) : turns.length === 0 ? (
            <div className="mx-auto flex h-full max-w-xl flex-col items-center justify-center py-6 text-center">
              <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-indigo-600 text-white shadow-lg shadow-brand-500/25">
                <Icon name="spark" className="h-6 w-6" />
              </span>
              <p className="mt-4 text-base font-semibold text-gray-900">What do you want to know about the reports?</p>
              <p className="mt-1 text-sm text-gray-500">Follow-up questions keep the context. Ask for answers in French, Spanish or Arabic.</p>
              <div className="mt-6 grid w-full gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s.text}
                    type="button"
                    onClick={() => ask(s.text)}
                    className="rounded-xl border border-gray-200 px-4 py-3 text-left transition hover:border-brand-300 hover:bg-brand-50/40"
                  >
                    <span className="block text-xs font-semibold text-brand-600">{s.title}</span>
                    <span className="mt-0.5 block text-sm text-gray-700">{s.text}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            turns.map((t, i) => <Turn key={i} turn={t} pending={streaming && i === turns.length - 1} />)
          )}
          {error && <ErrorBox message={error} />}
          <div ref={bottomRef} />
        </div>

        <form
          className="border-t border-gray-100 p-4"
          onSubmit={(e) => {
            e.preventDefault();
            ask(input);
          }}
        >
          <div className="flex items-end gap-2 rounded-2xl border border-gray-200 bg-white p-2 transition focus-within:border-brand-500 focus-within:ring-4 focus-within:ring-brand-100">
            <textarea
              aria-label="Message"
              dir="auto"
              rows={1}
              className="max-h-40 min-h-9 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-gray-900 outline-none [field-sizing:content] placeholder:text-gray-400"
              placeholder="Ask about the reports, e.g. Any ransomware reports from Nigeria?"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  ask(input);
                }
              }}
              maxLength={4000}
            />
            <button type="submit" className={`${primaryButton} h-9 px-3`} disabled={streaming || !input.trim()} aria-label="Send">
              {streaming ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" /> : <Icon name="send" />}
            </button>
          </div>
          <p className="mt-2 px-1 text-[11px] text-gray-400">Enter to send, Shift+Enter for a new line.</p>
        </form>
      </Card>

      <div className="space-y-6 self-start">
        <MemoryPanel version={memoryVersion} />
        <Card title="Agent tools">
          <ul className="flex flex-wrap gap-1.5 p-5">
            {TOOLS.map((t) => (
              <li key={t} className="rounded-md bg-gray-100 px-2 py-1 font-mono text-[11px] text-gray-700">
                {t}
              </li>
            ))}
          </ul>
          <p className="border-t border-gray-100 px-5 py-3 text-xs text-gray-500">Tools run fixed, parameterised SQL. The LLM never writes queries.</p>
        </Card>
      </div>
    </div>
    </>
  );
}

function Turn({ turn, pending }: { turn: ChatTurn; pending: boolean }) {
  if (turn.role === "user") {
    return (
      <div className="flex justify-end">
        <p dir="auto" className="max-w-[80%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-brand-600 px-4 py-2.5 text-sm text-white shadow-sm">
          {turn.content}
        </p>
      </div>
    );
  }
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-indigo-600 text-white">
        <Icon name="spark" />
      </span>
      <div className="min-w-0 max-w-[calc(100%-2.75rem)] flex-1 space-y-3">
        {turn.tool_calls.length > 0 && (
          <ol className="space-y-1.5 border-l-2 border-gray-100 pl-3">
            {turn.tool_calls.map((c) => (
              <ToolChip key={c.id} call={c} />
            ))}
          </ol>
        )}
        {turn.content ? (
          <div dir="auto" className="text-sm leading-relaxed text-gray-800">
            <RichText text={turn.content} />
          </div>
        ) : pending ? (
          <Spinner label={turn.tool_calls.length ? "Reading tool results…" : "Thinking…"} />
        ) : (
          <p className="text-sm text-gray-500">No answer.</p>
        )}
      </div>
    </div>
  );
}

function formatArgs(args: Record<string, unknown>): string {
  return Object.entries(args)
    .map(([k, v]) => `${k}=${typeof v === "string" ? (v.length > 40 ? v.slice(0, 40) + "…" : v) : JSON.stringify(v)}`)
    .join(", ");
}

function ToolChip({ call }: { call: ToolCall }) {
  return (
    <li>
      <details className="group rounded-lg text-xs">
        <summary className="flex cursor-pointer list-none items-center gap-2 rounded-lg px-2 py-1.5 font-mono text-gray-600 hover:bg-gray-50">
          {call.result === undefined ? (
            <span className="h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-gray-200 border-t-brand-500" />
          ) : (
            <span className="grid h-4 w-4 shrink-0 place-items-center rounded-full bg-emerald-100 text-emerald-600">
              <Icon name="check" className="h-3 w-3" />
            </span>
          )}
          <span className="truncate">
            <span className="font-semibold text-gray-900">{call.name}</span>({formatArgs(call.args)})
          </span>
          {call.result !== undefined && <span className="ml-auto shrink-0 font-sans text-gray-400 group-open:hidden">Show result</span>}
        </summary>
        {call.result !== undefined && (
          <div dir="auto" className="mt-1 max-h-60 overflow-auto whitespace-pre-wrap rounded-lg bg-gray-50 px-3 py-2 font-mono text-gray-600">
            <RichText text={call.result} />
          </div>
        )}
      </details>
    </li>
  );
}

function inline(text: string): ReactNode[] {
  return text.split(/(\[Report #\d+\]|\*\*[^*]+\*\*)/g).map((part, i) => {
    const ref = part.match(/^\[Report #(\d+)\]$/);
    if (ref)
      return (
        <a key={i} href={`#/reports/${ref[1]}`} className="inline-flex items-center rounded-md bg-brand-50 px-1.5 py-px font-mono text-xs font-semibold text-brand-700 ring-1 ring-inset ring-brand-100 hover:bg-brand-100">
          #{ref[1]}
        </a>
      );
    if (part.startsWith("**") && part.endsWith("**"))
      return (
        <strong key={i} className="font-semibold text-gray-900">
          {inline(part.slice(2, -2))}
        </strong>
      );
    return <Fragment key={i}>{part}</Fragment>;
  });
}

function RichText({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, i) => {
        const bullet = line.match(/^\s*[-*•]\s+(.*)/);
        if (bullet)
          return (
            <div key={i} className="flex gap-2 pl-1">
              <span className="text-gray-400">•</span>
              <span>{inline(bullet[1])}</span>
            </div>
          );
        return line.trim() ? <div key={i}>{inline(line)}</div> : <div key={i} className="h-2" />;
      })}
    </>
  );
}

function MemoryPanel({ version }: { version: number }) {
  const [prefs, setPrefs] = useState<Preference[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api
      .memory()
      .then(setPrefs)
      .catch((e) => setError(errorMessage(e)));
  }, []);

  useEffect(load, [load, version]);

  async function remove(id: number) {
    try {
      await api.deleteMemory(id);
      setPrefs((p) => p?.filter((x) => x.id !== id) ?? null);
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  return (
    <Card
      title={
        <span className="flex items-center gap-2">
          <Icon name="memory" className="h-4 w-4 text-brand-600" />
          Long-term memory
        </span>
      }
    >
      <div className="p-5">
        <p className="mb-3 text-xs text-gray-500">
          Long-term preferences the agent saved with <code>remember_preference</code>. They load into every new chat.
        </p>
        {error ? (
          <ErrorBox message={error} onRetry={load} />
        ) : prefs === null ? (
          <Spinner label="Loading…" />
        ) : prefs.length === 0 ? (
          <p className="rounded-xl bg-gray-50 px-3 py-4 text-center text-sm text-gray-500">
            Nothing saved yet. Try "Remember that I focus on West Africa".
          </p>
        ) : (
          <ul className="space-y-2">
            {prefs.map((p) => (
              <li key={p.id} className="group flex items-start justify-between gap-2 rounded-xl bg-gray-50 px-3 py-2.5 text-sm">
                <span dir="auto" className="text-gray-700">{p.text}</span>
                <button type="button" onClick={() => remove(p.id)} className="shrink-0 rounded-md p-0.5 text-gray-400 hover:bg-red-50 hover:text-red-600" aria-label={`Delete "${p.text}"`}>
                  <Icon name="trash" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}
