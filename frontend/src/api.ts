export type Location = { country: string; city: string | null };
export type Amount = { value: number; currency: string; context: string };

export type Report = {
  id: number;
  title: string;
  summary: string;
  original_language: string;
  crime_type: string;
  incident_date: string | null;
  confidence: number;
  source_name: string | null;
  created_at: string;
  locations: Location[];
};

export type ReportDetail = Report & {
  original_text: string;
  english_text: string;
  people: string[];
  organisations: string[];
  amounts: Amount[];
};

export type Filters = {
  crime_type?: string;
  country?: string;
  language?: string;
  date_from?: string;
  date_to?: string;
};

export type Health = { status: "ok" | "error"; provider: string; model: string | null; database?: string; error?: string };
export type Count = { key: string; count: number };
export type Stats = Record<"crime_type" | "country" | "language", Count[]>;
export type Preference = { id: number; text: string; created_at: string };

export type ToolCall = { id: string; name: string; args: Record<string, unknown>; result?: string };
export type ChatTurn = { role: "user" | "assistant"; content: string; tool_calls: ToolCall[] };

export type ChatEvent =
  | { type: "token"; text: string }
  | { type: "tool_call"; id: string; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; id: string; name: string; content: string }
  | { type: "error"; message: string }
  | { type: "done" };

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  const body = await res.json().catch(() => null);
  const detail = body?.detail;
  const message =
    typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((d: { msg: string }) => d.msg).join(", ")
        : `Request failed (${res.status})`;
  return new ApiError(message, res.status);
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError("Can't reach the API. Is the backend running on port 8000?", 0);
  }
  if (!res.ok) throw await toApiError(res);
  return res;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await send(path, init);
  return (res.status === 204 ? undefined : await res.json()) as T;
}

async function chat(threadId: string, message: string, onEvent: (e: ChatEvent) => void, signal?: AbortSignal) {
  const res = await send("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, message }),
    signal,
  });
  const reader = res.body!.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const data = chunk.match(/^data: (.*)$/m)?.[1];
      if (data) onEvent(JSON.parse(data) as ChatEvent);
    }
  }
}

export const api = {
  health: () => request<Health>("/api/health"),
  listReports: (filters: Filters) => {
    const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v) as [string, string][]);
    return request<Report[]>(`/api/reports?${params}`);
  },
  getReport: (id: number) => request<ReportDetail>(`/api/reports/${id}`),
  addReport: (input: { text?: string; file?: File }) => {
    const form = new FormData();
    if (input.file) form.append("file", input.file);
    else form.append("text", input.text ?? "");
    return request<ReportDetail>("/api/reports", { method: "POST", body: form });
  },
  stats: () => request<Stats>("/api/stats"),
  history: (threadId: string) => request<ChatTurn[]>(`/api/chat/${encodeURIComponent(threadId)}`),
  chat,
  memory: () => request<Preference[]>("/api/memory"),
  deleteMemory: (id: number) => request<void>(`/api/memory/${id}`, { method: "DELETE" }),
};
