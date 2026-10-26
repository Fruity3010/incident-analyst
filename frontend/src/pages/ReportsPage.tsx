import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Filters, type Report, type Stats } from "../api";
import {
  Card,
  Confidence,
  CRIME_TYPES,
  CrimeBadge,
  Empty,
  ErrorBox,
  Icon,
  LANGUAGES,
  LanguageBadge,
  PageHeader,
  Spinner,
  StatTile,
  countries,
  errorMessage,
  formatDate,
  inputClass,
  primaryButton,
  secondaryButton,
} from "../components/ui";

export default function ReportsPage() {
  const [filters, setFilters] = useState<Filters>({});
  const [reports, setReports] = useState<Report[] | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);

  const load = useCallback(() => {
    setError(null);
    setReports(null);
    api
      .listReports(filters)
      .then(setReports)
      .catch((e) => setError(errorMessage(e)));
  }, [filters]);

  useEffect(load, [load]);
  useEffect(() => {
    api.stats().then(setStats).catch(() => setStats(null));
  }, []);

  const hasFilters = Object.values(filters).some(Boolean);
  const set = (key: keyof Filters) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setFilters((f) => ({ ...f, [key]: e.target.value || undefined }));
  const total = stats?.crime_type.reduce((sum, c) => sum + c.count, 0);

  return (
    <>
      <PageHeader
        title="Reports"
        description="Public incident reports in English, French, Spanish and Arabic, translated and turned into structured fields by the LLM."
        actions={
          <button type="button" className={primaryButton} onClick={() => dialogRef.current?.showModal()}>
            <Icon name="plus" />
            Add report
          </button>
        }
      />

      <div className="mb-6 grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatTile label="Reports" value={total ?? "–"} icon="reports" />
        <StatTile label="Countries" value={stats?.country.length ?? "–"} icon="globe" />
        <StatTile label="Languages" value={stats?.language.length ?? "–"} icon="language" />
        <StatTile label="Crime types" value={stats?.crime_type.length ?? "–"} icon="tag" />
      </div>

      <Card>
        <div className="grid gap-2 border-b border-gray-100 p-4 sm:grid-cols-3 xl:grid-cols-5">
          <select aria-label="Crime type" className={inputClass} value={filters.crime_type ?? ""} onChange={set("crime_type")}>
            <option value="">All crime types</option>
            {Object.entries(CRIME_TYPES).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
          <input aria-label="Country" placeholder="Country, e.g. Nigeria" className={inputClass} value={filters.country ?? ""} onChange={set("country")} />
          <select aria-label="Language" className={inputClass} value={filters.language ?? ""} onChange={set("language")}>
            <option value="">All languages</option>
            {Object.entries(LANGUAGES).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
          <input aria-label="From date" title="Incident date from" type="date" className={inputClass} value={filters.date_from ?? ""} onChange={set("date_from")} />
          <input aria-label="To date" title="Incident date to" type="date" className={inputClass} value={filters.date_to ?? ""} onChange={set("date_to")} />
        </div>
        {hasFilters && (
          <div className="flex items-center justify-between border-b border-gray-100 bg-brand-50/40 px-5 py-2 text-xs text-gray-600">
            Filtered results
            <button type="button" className="font-semibold text-brand-600 hover:text-brand-700" onClick={() => setFilters({})}>
              Clear filters
            </button>
          </div>
        )}

        {error ? (
          <div className="p-5">
            <ErrorBox message={error} onRetry={load} />
          </div>
        ) : !reports ? (
          <div className="p-5">
            <Spinner label="Loading reports…" />
          </div>
        ) : reports.length === 0 ? (
          <Empty title={hasFilters ? "No reports match these filters" : "No reports yet"}>
            {hasFilters ? (
              <button type="button" className="text-brand-600 underline" onClick={() => setFilters({})}>
                Clear filters
              </button>
            ) : (
              <>
                Add one, or run <code className="rounded bg-gray-100 px-1">python seed.py</code> in backend/ to load the demo reports.
              </>
            )}
          </Empty>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs font-medium uppercase tracking-wide text-gray-500">
                <tr className="border-b border-gray-100">
                  <th className="px-5 py-3 font-medium">Report</th>
                  <th className="px-3 py-3 font-medium">Type</th>
                  <th className="px-3 py-3 font-medium">Lang</th>
                  <th className="px-3 py-3 font-medium">Countries</th>
                  <th className="px-3 py-3 font-medium">Incident date</th>
                  <th className="px-5 py-3 font-medium">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {reports.map((r) => (
                  <tr key={r.id} className="group cursor-pointer transition hover:bg-brand-50/40" onClick={() => (window.location.hash = `#/reports/${r.id}`)}>
                    <td className="max-w-md px-5 py-3.5">
                      <a href={`#/reports/${r.id}`} className="font-medium text-gray-900 group-hover:text-brand-700">
                        <span className="mr-1.5 font-mono text-xs text-gray-400">#{r.id}</span>
                        {r.title}
                      </a>
                      <p className="mt-0.5 truncate text-xs text-gray-500">{r.summary}</p>
                    </td>
                    <td className="px-3 py-3.5">
                      <CrimeBadge type={r.crime_type} />
                    </td>
                    <td className="px-3 py-3.5">
                      <LanguageBadge code={r.original_language} />
                    </td>
                    <td className="px-3 py-3.5 text-gray-600">{countries(r)}</td>
                    <td className="whitespace-nowrap px-3 py-3.5 text-gray-600">{formatDate(r.incident_date)}</td>
                    <td className="px-5 py-3.5">
                      <Confidence value={r.confidence} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <dialog ref={dialogRef} className="m-auto w-[min(36rem,calc(100vw-2rem))] rounded-2xl bg-white p-0 shadow-2xl">
        <AddReport onClose={() => dialogRef.current?.close()} onAdded={(r) => (window.location.hash = `#/reports/${r.id}`)} />
      </dialog>
    </>
  );
}

function AddReport({ onAdded, onClose }: { onAdded: (r: Report) => void; onClose: () => void }) {
  const [mode, setMode] = useState<"paste" | "upload">("paste");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ready = mode === "paste" ? text.trim().length >= 50 : !!file;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const report = await api.addReport(mode === "paste" ? { text } : { file: file! });
      onClose();
      onAdded(report);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <header className="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-4">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Add a report</h2>
          <p className="mt-0.5 text-sm text-gray-500">The agent detects the language, translates to English and extracts the key fields.</p>
        </div>
        <button type="button" onClick={onClose} disabled={busy} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600" aria-label="Close">
          <Icon name="close" />
        </button>
      </header>

      <div className="space-y-4 px-6 py-5">
        <div className="grid grid-cols-2 gap-1 rounded-xl bg-gray-100 p-1 text-sm font-medium">
          {(["paste", "upload"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`rounded-lg py-1.5 transition ${mode === m ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
            >
              {m === "paste" ? "Paste text" : "Upload file"}
            </button>
          ))}
        </div>

        {mode === "paste" ? (
          <div>
            <textarea
              aria-label="Article text"
              rows={10}
              className={`${inputClass} resize-y leading-relaxed`}
              placeholder="Paste a public news article or incident report in English, French, Spanish or Arabic…"
              value={text}
              onChange={(e) => setText(e.target.value)}
              dir="auto"
            />
            <p className="mt-1 text-right text-xs text-gray-400">{text.trim().length < 50 ? `${50 - text.trim().length} more characters needed` : `${text.length} characters`}</p>
          </div>
        ) : (
          <label className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-gray-200 px-4 py-10 text-center text-sm transition hover:border-brand-300 hover:bg-brand-50/40">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-50 text-brand-600">
              <Icon name="upload" className="h-5 w-5" />
            </span>
            <span className="font-semibold text-gray-900">{file ? file.name : "Choose a .txt or .pdf file"}</span>
            <span className="text-xs text-gray-500">Max 10 MB, text-based PDFs only</span>
            <input type="file" accept=".txt,.pdf" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>
        )}

        {error && <ErrorBox message={error} />}
        {busy && <Spinner label="Detecting language, translating and extracting fields. This can take up to a minute." />}
      </div>

      <footer className="flex justify-end gap-2 border-t border-gray-100 bg-gray-50/60 px-6 py-4">
        <button type="button" className={secondaryButton} onClick={onClose} disabled={busy}>
          Cancel
        </button>
        <button type="submit" disabled={!ready || busy} className={primaryButton}>
          {busy ? "Analysing…" : "Analyse and save"}
        </button>
      </footer>
    </form>
  );
}
