import { useEffect, useState } from "react";
import { api, type Count, type Stats } from "../api";
import { Card, CRIME_TYPES, Empty, ErrorBox, LANGUAGES, PageHeader, Spinner, StatTile, crimeDot, errorMessage } from "../components/ui";

export default function StatsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .stats()
      .then(setStats)
      .catch((e) => setError(errorMessage(e)));
  }, []);

  const header = <PageHeader title="Stats" description="Counts across every saved report. The agent's stats tool runs the same queries." />;
  if (error) return <>{header}<ErrorBox message={error} /></>;
  if (!stats) return <>{header}<Spinner label="Loading stats…" /></>;
  if (!stats.crime_type.length) return <>{header}<Card><Empty title="No reports yet" icon="stats">Add or seed reports to see statistics.</Empty></Card></>;

  const total = stats.crime_type.reduce((sum, c) => sum + c.count, 0);

  return (
    <>
      {header}
      <div className="mb-6 grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatTile label="Reports" value={total} icon="reports" />
        <StatTile label="Countries" value={stats.country.length} icon="globe" />
        <StatTile label="Languages" value={stats.language.length} icon="language" />
        <StatTile label="Crime types" value={stats.crime_type.length} icon="tag" />
      </div>
      <div className="grid items-start gap-6 lg:grid-cols-3">
        <Bars title="By crime type" rows={stats.crime_type} label={(k) => CRIME_TYPES[k] ?? k} dot={crimeDot} />
        <Bars title="By country" rows={stats.country} label={(k) => k} note="A report mentioning two countries counts in both." />
        <Bars title="By original language" rows={stats.language} label={(k) => LANGUAGES[k] ?? k} />
      </div>
    </>
  );
}

function Bars({ title, rows, label, note, dot }: { title: string; rows: Count[]; label: (key: string) => string; note?: string; dot?: (key: string) => string }) {
  const max = Math.max(...rows.map((r) => r.count), 1);
  return (
    <Card title={title}>
      <ul className="space-y-3 p-5">
        {rows.map((r) => (
          <li key={r.key} title={`${label(r.key)}: ${r.count}`}>
            <div className="mb-1 flex justify-between text-sm">
              <span className="flex items-center gap-2 text-gray-700">
                {dot && <span className={`h-2 w-2 rounded-full ${dot(r.key)}`} />}
                {label(r.key)}
              </span>
              <span className="font-medium tabular-nums text-gray-900">{r.count}</span>
            </div>
            <div className="h-2 rounded-full bg-gray-100">
              <div className="h-2 rounded-full bg-brand-500" style={{ width: `${(r.count / max) * 100}%` }} />
            </div>
          </li>
        ))}
      </ul>
      {note && <p className="border-t border-gray-100 px-5 py-2.5 text-xs text-gray-500">{note}</p>}
    </Card>
  );
}
