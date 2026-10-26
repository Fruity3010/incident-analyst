import { useEffect, useState, type ReactNode } from "react";
import { api, type ReportDetail } from "../api";
import { Card, Confidence, CrimeBadge, ErrorBox, Icon, LANGUAGES, LanguageBadge, Spinner, countries, errorMessage, formatDate } from "../components/ui";

export default function ReportDetailPage({ id }: { id: number }) {
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"original" | "english">("original");

  useEffect(() => {
    setReport(null);
    setError(null);
    setTab("original");
    api
      .getReport(id)
      .then(setReport)
      .catch((e) => setError(errorMessage(e)));
  }, [id]);

  const back = (
    <a href="#/reports" className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-gray-500 hover:text-gray-900">
      <Icon name="back" />
      All reports
    </a>
  );

  if (error)
    return (
      <div>
        {back}
        <ErrorBox message={error} />
      </div>
    );
  if (!report) return <Spinner label="Loading report…" />;

  const translated = report.original_language !== "en";
  const language = LANGUAGES[report.original_language] ?? report.original_language;

  return (
    <div>
      {back}
      <Card className="mb-6 overflow-hidden">
        <div className="bg-gradient-to-r from-chrome to-brand-900 px-6 py-6 text-white">
          <p className="font-mono text-xs text-white/60">REPORT #{report.id}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{report.title}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-white/75">{report.summary}</p>
        </div>
        <dl className="grid grid-cols-2 gap-px bg-gray-100 sm:grid-cols-3 lg:grid-cols-5">
          <Meta label="Crime type">
            <CrimeBadge type={report.crime_type} />
          </Meta>
          <Meta label="Language">
            <span className="flex items-center gap-2">
              <LanguageBadge code={report.original_language} />
              {language}
            </span>
          </Meta>
          <Meta label="Incident date">{formatDate(report.incident_date)}</Meta>
          <Meta label="Countries">{countries(report)}</Meta>
          <Meta label="Confidence">
            <Confidence value={report.confidence} />
          </Meta>
        </dl>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1fr_24rem]">
        <Card
          title={translated ? "Source text" : `Original (${language})`}
          actions={
            translated && (
              <div className="flex rounded-lg bg-gray-100 p-0.5 text-xs font-medium">
                {(["original", "english"] as const).map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setTab(t)}
                    className={`rounded-md px-3 py-1 transition ${tab === t ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
                  >
                    {t === "original" ? `Original (${language})` : "English translation"}
                  </button>
                ))}
              </div>
            )
          }
        >
          <p dir="auto" className="whitespace-pre-wrap px-6 py-5 text-[15px] leading-7 text-gray-700">
            {tab === "english" && translated ? report.english_text : report.original_text}
          </p>
          {report.source_name && <p className="border-t border-gray-100 px-6 py-3 text-xs text-gray-500">Source file: {report.source_name}</p>}
        </Card>

        <Card title="Extracted fields" className="self-start">
          <div className="space-y-5 p-5 text-sm">
            <Section label="Locations">
              <Chips items={report.locations.map((l) => (l.city ? `${l.city}, ${l.country}` : l.country))} />
            </Section>
            <Section label="People">
              <Chips items={report.people} />
            </Section>
            <Section label="Organisations">
              <Chips items={report.organisations} />
            </Section>
            <Section label="Amounts">
              {report.amounts.length ? (
                <ul className="space-y-2">
                  {report.amounts.map((a, i) => (
                    <li key={i} className="rounded-xl bg-gray-50 px-3 py-2">
                      <p className="font-semibold tabular-nums text-gray-900">
                        {a.value.toLocaleString("en-GB")} {a.currency}
                      </p>
                      <p className="text-xs text-gray-500">{a.context}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <None />
              )}
            </Section>
          </div>
        </Card>
      </div>
    </div>
  );
}

function Meta({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="bg-white px-5 py-3.5">
      <dt className="text-xs font-medium text-gray-500">{label}</dt>
      <dd className="mt-1 text-sm text-gray-900">{children}</dd>
    </div>
  );
}

function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</h3>
      {children}
    </div>
  );
}

function Chips({ items }: { items: string[] }) {
  if (!items.length) return <None />;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span key={item} dir="auto" className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs font-medium text-gray-700">
          {item}
        </span>
      ))}
    </div>
  );
}

function None() {
  return <p className="text-gray-400">None found</p>;
}
