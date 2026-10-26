import { useEffect, useState } from "react";
import { api, type Health } from "./api";
import ReportsPage from "./pages/ReportsPage";
import ReportDetailPage from "./pages/ReportDetailPage";
import AgentPage from "./pages/AgentPage";
import StatsPage from "./pages/StatsPage";
import { Icon, type IconName } from "./components/ui";

function useHashRoute(): string {
  const [hash, setHash] = useState(() => window.location.hash || "#/reports");
  useEffect(() => {
    const onChange = () => setHash(window.location.hash || "#/reports");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

const NAV: { href: string; label: string; icon: IconName }[] = [
  { href: "#/reports", label: "Reports", icon: "reports" },
  { href: "#/agent", label: "Ask the agent", icon: "agent" },
  { href: "#/stats", label: "Stats", icon: "stats" },
];

export default function App() {
  const route = useHashRoute();
  const [health, setHealth] = useState<Health | null | undefined>(undefined);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  const reportMatch = route.match(/^#\/reports\/(\d+)/);
  let page;
  if (reportMatch) page = <ReportDetailPage id={Number(reportMatch[1])} />;
  else if (route.startsWith("#/agent")) page = <AgentPage />;
  else if (route.startsWith("#/stats")) page = <StatsPage />;
  else page = <ReportsPage />;

  return (
    <div className="min-h-dvh lg:pl-64">
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col bg-chrome text-white lg:flex">
        <Brand />
        <nav className="flex-1 space-y-1 px-3 py-4">
          {NAV.map((item) => (
            <NavLink key={item.href} item={item} active={route.startsWith(item.href)} />
          ))}
        </nav>
        <div className="space-y-3 border-t border-white/10 p-4">
          <ProviderBadge health={health} />
          <p className="flex gap-2 text-[11px] leading-relaxed text-white/50">
            <Icon name="shield" className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            Demo for public news articles only. Don't upload real investigative, case or personal data. Sample reports are fictional.
          </p>
        </div>
      </aside>

      <header className="sticky top-0 z-20 bg-chrome text-white lg:hidden">
        <div className="flex h-14 items-center justify-between gap-3 px-4">
          <Brand compact />
          <ProviderBadge health={health} />
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-2">
          {NAV.map((item) => (
            <NavLink key={item.href} item={item} active={route.startsWith(item.href)} />
          ))}
        </nav>
        <p className="bg-amber-50 px-4 py-1.5 text-center text-[11px] text-amber-800">Demo for public news articles only. Sample reports are fictional.</p>
      </header>

      {health?.status === "error" && (
        <div role="alert" className="border-b border-red-200 bg-red-50 px-4 py-2 text-center text-sm text-red-700">
          {health.error}
        </div>
      )}

      <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-8 lg:py-10">{page}</main>
    </div>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <a href="#/reports" className={`flex items-center gap-3 font-semibold ${compact ? "" : "h-16 border-b border-white/10 px-5"}`}>
      <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-brand-500 to-indigo-600 shadow-lg shadow-brand-900/40">
        <Icon name="shield" className="h-4.5 w-4.5" />
      </span>
      <span className="leading-tight">
        <span className="block text-sm">Incident Report</span>
        <span className="block text-xs font-medium text-white/60">Analyst Agent</span>
      </span>
    </a>
  );
}

function NavLink({ item, active }: { item: (typeof NAV)[number]; active: boolean }) {
  return (
    <a
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={`flex shrink-0 items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${active ? "bg-white/10 text-white" : "text-white/60 hover:bg-white/5 hover:text-white"}`}
    >
      <Icon name={item.icon} className="h-4.5 w-4.5" />
      {item.label}
    </a>
  );
}

function ProviderBadge({ health }: { health: Health | null | undefined }) {
  if (health === undefined) return <span className="text-xs text-white/50">Connecting…</span>;
  const ok = health?.status === "ok";
  const dot = !health ? "bg-red-500" : ok ? "bg-emerald-400" : "bg-amber-400";
  const label = !health ? "API offline" : ok ? `${health.provider} · ${health.model}` : `${health.provider} not configured`;
  return (
    <span className="flex items-center gap-2 rounded-lg bg-white/5 px-2.5 py-1.5 text-xs font-medium ring-1 ring-white/10" title={health?.database ? `Database: ${health.database}` : undefined}>
      <span className="relative flex h-2 w-2">
        {ok && <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${dot}`} />}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${dot}`} />
      </span>
      <span className="max-w-[40vw] truncate lg:max-w-44">{label}</span>
    </span>
  );
}
